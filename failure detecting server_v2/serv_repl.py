#!/usr/bin/env python3

import socket, sys, os, signal, threading
import szasar, time

SERVER = 'localhost'
PORT = 6012 #backup server
PORT2 = 6013 #main server
FILES_PATH = "filesbu"
MAX_FILE_SIZE = 10 * 1 << 20 # 10 MiB
SPACE_MARGIN = 50 * 1 << 20  # 50 MiB
USERS = ("anonimous", "sar", "sza")
PASSWORDS = ("", "sar", "sza")
backuplist = []
backuplistescuchar = []
primary = None

class State:
	Identification, Authentication, Main, Downloading, Uploading = range(5)

def sendOK( s, params="" ):
	s.sendall( ("OK{}\r\n".format( params )).encode( "ascii" ) )

def sendER( s, code=1 ):
	s.sendall( ("ER{}\r\n".format( code )).encode( "ascii" ) )

def sendBEAT( s ):
	s.sendall( ("B\r\n".encode( "ascii" )))

def separate_path(filename):
	a = str(filename)
	d = a.split("/")
	return d

def beat(p):
	print("Estoy en Beat")
	slist = []
	slist.append(p)
	sendBEAT(p)
	#p.sendall(("BE\r\n").encode("ascii")) #queremos enviar el mensaje m al processo
	ready = select.select(slist, [], [], 7000)
	if not ready[0]:
		print("Not ready. Beat mal: " + message)
		return False
	else:
		message = szasar.recvline( p ).decode( "ascii" )
		if message.startswith("B"): #if ok
			print("Beat bien")
			return True
		else:
			print("Beat mal: " + message)
			return False

def heartbeat(backuplist):
	#print("en la slist hay: " + str(slist))
	slist2 = []
	slist2.append(slist)
	while True:
		time.sleep(2)
		for process in slist2: #for every process in the list of sockets
			print("Sending beat to process")
			response = beat(process) #sending message q to every process
			if(response == False and process == primary):
				print("Hay que implementar lo de nuevo primario")
				electNewPrimary()
			elif(response == False and process != primary):
				print("deslistar al servidor no primario de la lista de backup")
				backuplist.remove(process)

def electNewPrimary():
	for process in backuplist:
		process.sendall( ("ELON\r\n".encode( "ascii" )))
		ready = select.select([process], [], [], 7000)
		if not ready[0]:
			continue
		else:
			message = szasar.recvline( s ).decode( "ascii" )
			if(message.startswith("OK")):
				primary = process


def session( s, i ):
	state = State.Identification
	f_path = FILES_PATH + str(i)
	while True:
		#print("Hola soy el serverBU{}. Mi filepath es: {}".format(i, f_path))
		message = szasar.recvline( s ).decode( "ascii" )
		#print("RECV: Estado: " + str(state) + "Msg: " + message)
		if not message:
			return

		if message.startswith( szasar.Command.User ):
			if( state != State.Identification ):
				sendER( s )
				continue
			try:
				user = USERS.index( message[4:] )
				username = message[4:]
				#filespath = os.path.join( f_path, "sar" ) Poniendo esto, todos los usuarios suben sus archivos a la carpeta sar
				filespath = os.path.join( f_path, username )
				sendOK( s )
				helbidea, portua = s.getsockname()
				helbidea2 = s.getpeername()
				state = State.Main
			except Exception as e:
				#print("ERROR en ID: usuario recibido: {}" + str(message[4:]) + "yep")
				#print("Error en la identificacion")
				print(e)
				#sendER( s, 2 )
		elif message.startswith(szasar.Command.Elon):
			sendOK(s)
		elif message.startswith(szasar.Command.Sock):
			sockets =  s.recv(4096)
			sockets = sockets[4:-1]
			backuplistescuchar = [None]*int((len(sockets)/2))
			i = 0
			j = 0
			while(i < len(sockets)-1):
				helbidea = sockets[i]
				portua = sockets[i+1]
				backuplistescuchar[j] = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
				try:
					backuplistescuchar[j].bind(('', portua))
					print("bind bien en la sincronizacion de sockets")
				except socket.error as msg:
					print('Bind falla en la sincronizacion de sockets: ' + str(msg))
					sys.exit()
				backuplistescuchar[j].listen( 5 )
				j = j+1
				i=i+2
			time.sleep(3)
			j = 0
			i = 0
			backuplist = [None]*int((len(sockets)/2))
			while(i < len(sockets)-1):
				helbidea = sockets[i]
				portua = sockets[i+1]
				backuplist[j] = socket.socket( socket.AF_INET, socket.SOCK_STREAM ) #Create new socket for each server.
				backuplist[j].connect( (helbidea, portua))
				j = j+1
				i = i+2




		elif message.startswith( szasar.Command.Password ):
			if state != State.Authentication:
				sendER( s )
				continue
			if( user == 0 or PASSWORDS[user] == message[4:] ):
				sendOK( s )
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
				for filename in os.listdir( f_path ):
					filesize = os.path.getsize( os.path.join( f_path, filename ) )
					message += "{}?{}\r\n".format( filename, filesize )
				message += "\r\n"
			except:
				sendER( s, 4 )
			else:
				s.sendall( message.encode( "ascii" ) )

		elif message.startswith( szasar.Command.Download ):
			print("Mensaje de descarga detectado")
			if state != State.Main:
				sendER( s )
				continue
			filename = os.path.join( f_path, message[4:] )
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
			state = State.Identification
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
			svfs = os.statvfs( f_path )
			if filesize + SPACE_MARGIN > svfs.f_bsize * svfs.f_bavail:
				sendER( s, 9 )
				continue
			sendOK( s )
			state = State.Uploading

		elif message.startswith( szasar.Command.Upload2 ):
			if state != State.Uploading:
				sendER( s )
				continue
			state = State.Identification
			try:
				print("1")
				directories = separate_path(filename)
				for i in range(len(directories)):
					print("2")
					if i==0:
						print("21")
						finalpath = ""
						print("finalpath: " + finalpath + " filename: " + filename + " filespath: " + filespath)
					else:
						print("22")
						finalpath = os.path.join(finalpath,directories[i])
						print("3")
						if(os.path.exists(os.path.join( filespath, finalpath))==False):
							print("4")
							if(i!=len(directories)-1):
								print("5")
								os.mkdir(os.path.join( filespath, finalpath))
								print("6")
				with open( os.path.join( filespath, filename), "wb" ) as f:
					print("7")
					filedata = szasar.recvall( s, filesize )
					print("8")
					f.write( filedata )
					print("9")
				#print (e) #este print hacia que entrara en el except
			except:
				print("He entrado en el except del upload 2")
				sendER( s, 10 )
			else:
				sendOK( s )

		elif message.startswith( szasar.Command.Delete ):
			if state != State.Main:
				sendER( s )
				continue
			if user == 0:
				sendER( s, 7 )
				continue
			state = State.Identification
			try:
				os.remove( os.path.join( filespath, message[4:] ) )
			except:
				sendER( s, 11 )
			else:
				sendOK( s )

		elif message.startswith( szasar.Command.Exit ):
			sendOK( s )
			return

		elif message.startswith(szasar.Command.Beat):
			print("Session: Msg identificado como beat")
			sendBEAT( s )

		elif message.startswith(szasar.Command.Update ):
			print("Mensaje identificado como update")
			if state != State.Main:
				sendER( s )
				continue
			try:
				message = "OK\r\n"
				for filename in os.listdir( filespath ):
					with open( filename, "rb" ) as f:
						filedata = f.read()
					message += "{}?{}?\r\n".format( filename, filedata )
				message += "\r\n"
				#siempre se envia el mensaje asi: nombre?contenido
			except:
				sendER( s, 4 )
			else:
				s.sendall( message.encode( "ascii" ) )

		else:
			sendER( s )



if __name__ == "__main__":
	n = sys.argv[1]
	print("Se van a crear {} backup servers".format(n))
	#Connection with the main server
	for i in range(int(n)):
		PORT2 = PORT2 + i
		try:
			s = socket.socket( socket.AF_INET, socket.SOCK_STREAM ) #Create new socket for each server.
			print("Intento {} de {} de conectarse a main server".format(i, n))
			s.connect( (SERVER, PORT2))
			primary = s
		except socket.error as msg:
			print(msg)
			sys.exit()

		print( "Conexión aceptada del socket SERVER {} de {} = {}:{}.".format(i, n, SERVER, PORT2) )

		t = threading.Thread(target=session, args=(s, i,))
		t.start()
		t2 = threading.Thread(target=heartbeat, args=())
