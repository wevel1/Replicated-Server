#!/usr/bin/env python3

import socket, sys, os, signal
import szasar

SERVER = 'localhost'
PORT = 6013
FILES_PATH = "files"
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
		message = szasar.recvline( s ).decode( "ascii" )
		if not message:
			return

		if message.startswith( szasar.Command.User ):
			if( state != State.Identification ):
				sendER( s )
				continue
			try:
				user = USERS.index( message[4:] )
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
				for filename in os.listdir( FILES_PATH ):
					filesize = os.path.getsize( os.path.join( FILES_PATH, filename ) )
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
			svfs = os.statvfs( FILES_PATH )
			if filesize + SPACE_MARGIN > svfs.f_bsize * svfs.f_bavail:
				print("llega error 4")
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
				directories = separate_path(filename)
				for i in range(len(directories)):
					if i==0:
						finalpath = ""
					else:
						finalpath = os.path.join(finalpath,directories[i])
						if(os.path.exists(os.path.join( FILES_PATH, finalpath))==False):
							if(i!=len(directories)-1):
								os.mkdir(os.path.join( FILES_PATH, finalpath))
				with open( os.path.join( FILES_PATH, finalpath), "wb" ) as f:
					filedata = szasar.recvall( s, filesize )
					f.write( filedata )
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
			try:
				os.remove( os.path.join( FILES_PATH, message[4:] ) )
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
	s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
    
    #Connection with the main server
	try:
		s.connect( (SERVER, PORT) )
	except socket.error as msg:
		print('Connection failed with main server. Error Code : ...')
		sys.exit()
	
	print('Socket bind complete with main server')

	signal.signal(signal.SIGCHLD, signal.SIG_IGN)

	while True:
		if(1==0):
			print('kaixo')
			#Aqui iria parte del codigo.