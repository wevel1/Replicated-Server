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

def separate_path(filename):
	a = str(filename)
	d = a.split("/")
	return d

def session( s ):
	state = State.Identification

	while True:
		print("Hola soy el serverBU")
		message = szasar.recvline( s2 ).decode( "ascii" )
		print("Mezu bat jasota. Estado: " + str(state))
		print("Mezu bat jasota. Msg: " + message)
		if not message:
			print("No habia mensaje en sBU")
			return

		if message.startswith( szasar.Command.User ):
			print("sBU ha entrado en user")
			if( state != State.Identification ):
				sendER( s )
				continue
			try:
				user = USERS.index( message[4:] )
				username = message[4:]
				filespath = os.path.join( FILES_PATH, username )
				print("Identification realizada: "+ username)
				sendOK(s)
				s.sendall( ("OK\r\n".encode( "ascii" ) ) )
				print("OKIdent enviado")
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
				# for filename in os.listdir( FILES_PATH ):
					# filesize = os.path.getsize( os.path.join( FILES_PATH, filename ) )
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
			filename = os.path.join( FILES_PATH, message[4:] )
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
			print("Mensaje de subida detectado")
			if state != State.Main:
				sendER( s )
				continue
			if user == 0:
				sendER( s, 7 )
				continue
			filename, filesize = message[4:].split('?')
			filesize = int(filesize)
			if filesize > MAX_FILE_SIZE:
				print("llega error 3")
				sendER( s, 8 )
				continue
			svfs = os.statvfs( FILES_PATH )
			if filesize + SPACE_MARGIN > svfs.f_bsize * svfs.f_bavail:
				print("llega error 4")
				sendER( s, 9 )
				continue
			print("OK1 enviando")
			sendOK( s )
			print("Subida1 completada. filename: {} filesize: {} ".format(filename, filesize))
			state = State.Uploading

		elif message.startswith( szasar.Command.Upload2 ):
			print("Fase 2 de la subida")
			if state != State.Uploading:
				sendER( s )
				continue
			state = State.Identification
			try:
				directories = separate_path(filename)
				print("len(directories): " + str(len(directories)))
				for i in range(len(directories)):
					if i==0:
						print("i es 0")
						finalpath = ""
					else:
						finalpath = os.path.join(finalpath,directories[i])
						print("finalpath: " + finalpath)
						if(os.path.exists(os.path.join( filespath, finalpath))==False):
							if(i!=len(directories)-1):
								os.mkdir(os.path.join( filespath, finalpath))
				print("hemos salido del FOR")
				with open( os.path.join( filespath, filename), "wb" ) as f:
					print("Hemos abierto el path")
					filedata = szasar.recvall( s, filesize )
					print("Hemos recibido la información")
					f.write( filedata )
					print("Hemos escrito los datos")
			except Exception as e:
				print (e)
				sendER( s, 10 )
			else:
				print("OK2 enviado")
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
				sendOK( s )

		elif message.startswith( szasar.Command.Exit ):
			sendOK( s )
			return

		else:
			sendER( s )



if __name__ == "__main__":
	s = socket.socket( socket.AF_INET, socket.SOCK_STREAM ) #socket de enviar al main
	s2 = socket.socket( socket.AF_INET, socket.SOCK_STREAM ) #socket de recibir del main

	#Connection with the main server

	try:
		s.connect( (SERVER, PORT2) )
	except socket.error as msg:
		print('Connection failed with main server. Error Code : ...')
		sys.exit()

	#s.listen(5)
	#s.accept()

	try:
		#s2.bind(('', PORT))
		s2.connect( (SERVER, PORT2) )
	except socket.error as msg:
		print('Connection failed with backup server. Error Code : ...')
		sys.exit()

	#s2.listen( 5 )
	#s2.accept()

	#signal.signal(signal.SIGCHLD, signal.SIG_IGN)

	print( "Conexión aceptada del socket SERVER {}:{}.".format( SERVER, PORT2 ) )


	t = threading.Thread(target=session, args=(s,))
	t.start()
