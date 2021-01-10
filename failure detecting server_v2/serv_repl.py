#!/usr/bin/env python3

import socket, sys, os, signal, threading
import szasar

SERVER = 'localhost'
PORT = 6012 #backup server
PORT2 = 6013 #main server
FILES_PATH = "filesbu"
MAX_FILE_SIZE = 10 * 1 << 20 # 10 MiB
SPACE_MARGIN = 50 * 1 << 20  # 50 MiB
USERS = ("anonimous", "sar", "sza")
PASSWORDS = ("", "sar", "sza")

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

def heartbeat(slist):
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
			elif(response == False and process != primary):
				print("deslistar al servidor no primario de la lista de backup")


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


		# elif message.startswith( szasar.Command.Password ):
			# if state != State.Authentication:
				# sendER( s )
				# continue
			# if( user == 0 or PASSWORDS[user] == message[4:] ):
				# sendOK( s )
				# state = State.Main
			# else:
				# sendER( s, 3 )
				# state = State.Identification

		# elif message.startswith( szasar.Command.List ):
			# if state != State.Main:
				# sendER( s )
				# continue
			# try:
				# message = "OK\r\n"
				# for filename in os.listdir( f_path ):
					# filesize = os.path.getsize( os.path.join( f_path, filename ) )
					# message += "{}?{}\r\n".format( filename, filesize )
				# message += "\r\n"
			# except:
				# sendER( s, 4 )
			# else:
				# s.sendall( message.encode( "ascii" ) )

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
				directories = separate_path(filename)
				for i in range(len(directories)):
					if i==0:
						finalpath = ""
					else:
						finalpath = os.path.join(finalpath,directories[i])
						if(os.path.exists(os.path.join( filespath, finalpath))==False):
							if(i!=len(directories)-1):
								os.mkdir(os.path.join( filespath, finalpath))
				with open( os.path.join( filespath, filename), "wb" ) as f:
					filedata = szasar.recvall( s, filesize )
					f.write( filedata )
				print (e)
			except:
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
			
		else:
			sendER( s )



if __name__ == "__main__":
	n = sys.argv[1]
	print("Se van a crear {} backup servers".format(n))
	#Connection with the main server
	for i in range(int(n)):
		try:
			s = socket.socket( socket.AF_INET, socket.SOCK_STREAM ) #Create new socket for each server.
			print("Intento {} de {} de conectarse a main server".format(i, n))
			s.connect( (SERVER, PORT2 ))
		except socket.error as msg:
			print(msg)
			sys.exit()
			
		print( "Conexión aceptada del socket SERVER {} de {} = {}:{}.".format(i, n, SERVER, PORT2 ) )

		t = threading.Thread(target=session, args=(s, i,))
		t.start()
