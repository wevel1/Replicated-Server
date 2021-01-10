#!/usr/bin/env python3

import time #used for sleep mainly
import socket, sys, os, signal, threading
import szasar, select

PORT = 6012
PORT2 = 6013
FILES_PATH = "files"
MAX_FILE_SIZE = 10 * 1 << 20 # 10 MiB
SPACE_MARGIN = 50 * 1 << 20  # 50 MiB
USERS = ("anonimous", "sar", "sza")
PASSWORDS = ("", "sar", "sza")
backuplist = []
socketlist = []
primary = None

ER_MSG = (
	"Correcto.",
	"Comando desconocido o inesperado.",
	"Usuario desconocido.",
	"Clave de paso o password incorrecto.",
	"Error al crear la lista de ficheros.",
	"El fichero no existe.",
	"Error al bajar el fichero.",
	"Un usuario anonimo no tiene permisos para esta operacion.",
	"El fichero es demasiado grande.",
	"Error al preparar el fichero para subirlo.",
	"Error al subir el fichero.",
	"Error al borrar el fichero." )

def iserror( message ):
	if( message.startswith( "ER" ) ):
		code = int( message[2:] )
		print( ER_MSG[code] )
		return True
	else:
		return False

class State:
	Identification, Authentication, Main, Downloading, Uploading = range(5)

def sendOK( s, params="" ):
	s.sendall( ("OK{}\r\n".format( params )).encode( "ascii" ) )

def sendER( s, code=1 ):
	s.sendall( ("ER{}\r\n".format( code )).encode( "ascii" ) )

def sendBEAT( s ):
	s.sendall( ("B\r\n".encode( "ascii" )))

def sendBU( sBU, user, filename, filesize, filedata ):
	#Identification phase
	message = "{}{}\r\n".format( szasar.Command.User, user )
	sBU.sendall( message.encode( "ascii" ) )
	message = szasar.recvline( sBU ).decode( "ascii" )
	if not iserror( message ):
		print("Identification has been done correctly with the BackupServer")
	else:
		print("Has not been possible to identify on the backup server")
		return

	#UPLOAD1
	message = "{}{}?{}\r\n".format( szasar.Command.Upload, filename, filesize )
	sBU.sendall( message.encode( "ascii" ) )
	message = szasar.recvline( sBU ).decode( "ascii" )
	if not iserror( message ):
		print("UPLOAD1 has been done correctly with the BackupServer ")
	else:
		print("Has not been possible to make UPLOAD1 on the BackupServer")
		return

	#UPLOAD2
	print(" ======= UPLOAD2 ======= ")
	message = "{}\r\n".format( szasar.Command.Upload2 )
	sBU.sendall( message.encode( "ascii" ) )
	sBU.sendall( filedata )
	print("Upload2 enviado")
	message = szasar.recvline( sBU ).decode( "ascii" )
	if not iserror( message ):
		print( "The file {} has been uploaded correctly to the BackupServer".format( filename) )
	else:
		print("Has not been possible to make UPLOAD2 on the BackupServer")

def deleteBU( sBU, user, filename ):
	
	#Identification phase
	message = "{}{}\r\n".format( szasar.Command.User, user )
	sBU.sendall( message.encode( "ascii" ) )
	message = szasar.recvline( sBU ).decode( "ascii" )
	if not iserror( message ):
		print("Identification has been done correctly with the BackupServer")
	else:
		print("Has not been possible to make UPLOAD2 on the BackupServer")
		return
		
	#Delete phase
	message = "{}{}\r\n".format( szasar.Command.Delete, filename )
	sBU.sendall( message.encode( "ascii" ) )
	message = szasar.recvline( sBU ).decode( "ascii" )
	if not iserror( message ):
		print("Delete has been done correctly with the BackupServer")
	else:
		print("Has not been possible to make delete on the BackupServer")
		return

def beat(p):
	print("=== BEAT ===")
	slist = []
	slist.append(p)
	sendBEAT(p) 
	ready = select.select(slist, [], [], 30)
	if not ready[0]:
		print("Not ready. Timeout ocurred")
		return False
	else:
		try:
			message = szasar.recvline( p ).decode( "ascii" )
			if message.startswith("B"): #if ok
				print("+++++++ Beat bien")
				return True
		except:
			print("Beat mal... :( ")
			return False	
	
def heartbeat():
	time.sleep(2)
	print("===HEARTBEAT===")
	print("HB: En la slist hay: " + str(len(backuplist)))
	while True:
		time.sleep(2)
		for process in backuplist: #for every process in the list of sockets
			helbidea, portua = s.getsockname()
			print("Sending beat to process {}:{}".format(helbidea, portua))
			response = beat(process) #sending message q to every process
			if(response == False and process == primary):
				print("Hay que implementar lo de nuevo primario")
			elif(response == False and process != primary):
				print("deslistar al servidor no primario de la lista de backup")
				backuplist.remove(process)
		print(" =!=!=!=!=!=!=!=!=!=!=!=!=!=!=!=!")


def session( s , backuplist):
	state = State.Identification

	while True:
		#print("---SERVER: A la espera de un mensaje........................")
		message = szasar.recvline( s ).decode( "ascii" )
		#print( "---SERVER: Leido msg {} {}\r\n.".format( message[0:4], message[4:] ) )
		if not message:
			return

		if message.startswith( szasar.Command.User ):
			if( state != State.Identification ):
				sendER( s )
				continue
			try:
				user = USERS.index( message[4:] )
				username = message[4:]
			except:
				sendER( s, 2 )
			else:
				sendOK( s )
				state = State.Authentication

		elif message.startswith( szasar.Command.Password ):
			if state != State.Authentication:
				sendER( s )
				continue
			if( user == 0 or PASSWORDS[user] == message[4:] ):
				sendOK( s )
				filespath = os.path.join( FILES_PATH, USERS[user] )
				state = State.Main
			else:
				sendER( s, 3 )
				state = State.Identification

		elif message.startswith( szasar.Command.List ):
			if state != State.Main:
				sendER( s )
				continue
			try:
				message = "OK\r\n"
				for filename in os.listdir( filespath ):
					filesize = os.path.getsize( os.path.join( filespath, filename ) )
					message += "{}?{}\r\n".format( filename, filesize )
				message += "\r\n"
			except:
				sendER( s, 4 )
			else:
				s.sendall( message.encode( "ascii" ) )

		elif message.startswith( szasar.Command.Download ):
			if state != State.Main:
				sendER( s )
				continue
			filename = os.path.join( filespath, message[4:] )
			try:
				filesize = os.path.getsize( filename )
			except:
				sendER( s, 5 )
				continue
			else:
				sendOK( s, filesize )
				state = State.Downloading

		elif message.startswith( szasar.Command.Download2 ):
			if state != State.Downloading:
				sendER( s )
				continue
			state = State.Main
			try:
				with open( filename, "rb" ) as f:
					filedata = f.read()
			except:
				sendER( s, 6 )
			else:
				sendOK( s )
				s.sendall( filedata )

		elif message.startswith( szasar.Command.Upload ):
			if state != State.Main:
				sendER( s )
				continue
			if user == 0:
				sendER( s, 7 )
				continue
			filename, filesize = message[4:].split('?')
			filesize = int(filesize)
			if filesize > MAX_FILE_SIZE:
				sendER( s, 8 )
				continue
			svfs = os.statvfs( filespath )
			if filesize + SPACE_MARGIN > svfs.f_bsize * svfs.f_bavail:
				sendER( s, 9 )
				continue
			sendOK( s )
			state = State.Uploading

		elif message.startswith( szasar.Command.Upload2 ):
			if state != State.Uploading:
				sendER( s )
				continue
			state = State.Main
			try:
				with open( os.path.join( filespath, filename), "wb" ) as f:
					filedata = szasar.recvall( s, filesize )
					f.write( filedata )
			except:
				sendER( s, 10 )
			else:
				#Upload to the secondary servers before sending ACK to the client
				for i in backuplist:
					sendBU(i, username, filename, filesize, filedata)
				sendOK( s )

		elif message.startswith( szasar.Command.Delete ):
			if state != State.Main:
				sendER( s )
				continue
			if user == 0:
				sendER( s, 7 )
				continue
			try:
				os.remove( os.path.join( filespath, message[4:] ) )
			except:
				sendER( s, 11 )
			else:
				#Delete from the secondary servers before sending ACK to the client
				for i in backuplist:
					deleteBU(i, username, message[4:])
				sendOK( s )

		elif message.startswith( szasar.Command.Exit ):
			sendOK( s )
			s.close()
			return
		
		elif message.startswith(szasar.Command.Beat):
			print("Session: Msg identificado como beat")
			#sendBEAT( s )
		else:
			sendER( s )



if __name__ == "__main__":
	s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
	s2 = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
	s3 = socket.socket( socket.AF_INET, socket.SOCK_STREAM )

	#Connection with the client.
	try:
		s.bind(('', PORT))
		print("Bind with clients succesfull")
	except socket.error as msg:
		print('Bind failed with client. Error Code : ' + str(msg))
		sys.exit()
	s.listen( 5 )

	#Connection with replicated server1 and server2
	try:
		s2.bind(('', PORT2))
		print("Bind with backup servers succesfull")
	except socket.error as msg:
		print('Bind failed replicated server 1 or 2. Error Code : ...')
		sys.exit()
	s2.listen( 5 )

	signal.signal(signal.SIGCHLD, signal.SIG_IGN)
	socketlist = []
	socketlist.append(s)
	socketlist.append(s2)

	threads = []
	dialog = []

	primary = s
	i = 0
	while (True):
		readable,_,_ = select.select(socketlist, [], [])
		ready_server = readable[0]
		helbidea, portua = ready_server.getsockname()
		print("Puerto: " + str(portua))
		if portua == 6013:
			sc, address = ready_server.accept()
			print( "Conexión aceptada del socket SERVER {0[0]}:{0[1]}.".format( address ) )
			backuplist.append(sc)
			if i == 0 :
				t2 = threading.Thread(target=heartbeat, args=())
				t2.start()
				i = 1
		elif portua == 6012:
			sc, address = ready_server.accept()
			print( "Conexión aceptada del socket CLIENTE {0[0]}:{0[1]}.".format( address ) )
			dialog.append(sc)
			t = threading.Thread(target=session, args=(dialog[-1], backuplist))
			threads.append(t)
			t.start()

		
