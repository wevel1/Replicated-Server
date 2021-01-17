 # Lectura de stdin en python
import socket, sys, os
import szasar
import time
SERVER = 'localhost'
PORT = 6012
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

class Menu:
	List, Download, Upload, Delete, Exit, Modify = range( 1, 6 )
	Options = ( "Lista de ficheros", "Bajar fichero", "Subir fichero", "Borrar fichero", "Salir" )
	
def operation():
	while 1:
		# Obtener el nombre del archivo.
		line = sys.stdin.readline()	#Cuando recibe un input finalizado en \n, lo guarda en line.
		if not line:
			time.sleep(3)
			break
		else:
			operation = line.rstrip('\n')


		# Obtener el numero, que nos indicará que tipo de operación se ha realizado (crear, borrar...)
		line = sys.stdin.readline()	#Cuando recibe un input finalizado en \n, lo guarda en line.
		if not line:
			break
		else:
			filename = line.rstrip('\n')	

		line = sys.stdin.readline()	#Cuando recibe un input finalizado en \n, lo guarda en line.
		if not line:
			break
		else:
			path = line.rstrip('\n')

		print("OPERATION - option: "+operation+"filename: "+filename)
		return operation,filename,path
		'''
		if not line:
			break
		else
			if line.isnumeric() :
			operation = line;
		'''

def iserror( message ):
	if( message.startswith( "ER" ) ):
		code = int( message[2:] )
		print( ER_MSG[code] )
		return True
	else:
		return False


if __name__ == "__main__":
	if len( sys.argv ) > 3:
		print( "Uso: {} [<servidor> [<puerto>]]".format( sys.argv[0] ) )
		exit( 2 )

	#if len( sys.argv ) >= 2:
	#	SERVER = sys.argv[1]
	#if len( sys.argv ) == 3:
	#	PORT = int( sys.argv[2])

	s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
	s.connect( (SERVER, PORT) )

	
	while True:
		#user = input( "Introduce el nombre de usuario: " )
		user= sys.argv[1]
		message = "{}{}\r\n".format( szasar.Command.User, user )
		s.sendall( message.encode( "ascii" ) )
		message = szasar.recvline( s ).decode( "ascii" )
		if iserror( message ):
			continue

		#password = input( "Introduce la contraseña: " )
		password= sys.argv[2]
		message = "{}{}\r\n".format( szasar.Command.Password, password )
		s.sendall( message.encode( "ascii" ) )
		message = szasar.recvline( s ).decode( "ascii" )
		if not iserror( message ):
			break


	while True:
		print("llamada a operation")
		option,filename,path = operation()
		print("MAIN: opcion es: "+option+" MAIN: y filename= "+filename+" con path "+path)
		filename= str(filename)

		if int(option) == Menu.Download:
			message = "{}{}\r\n".format( szasar.Command.Download, filename )
			s.sendall( message.encode( "ascii" ) )
			message = szasar.recvline( s ).decode ("ascii" )
			if iserror( message ):
				continue
			filesize = int( message[2:] )
			message = "{}\r\n".format( szasar.Command.Download2 )
			s.sendall( message.encode( "ascii" ) )
			message = szasar.recvline( s ).decode( "ascii" )
			if iserror( message ):
				continue
			filedata = szasar.recvall( s, filesize )
			try:
				with open( filename, "wb" ) as f:
					f.write( filedata )
			except:
				print( "No se ha podido guardar el fichero en disco." )
			else:
				print( "El fichero {} se ha descargado correctamente.".format( filename ) )
		elif int(option) == Menu.Upload:
			try:

				prueba = os.path.join(path,filename)
				filesize = os.path.getsize(prueba)
				with open(prueba, "rb" ) as f:
					filedata = f.read()
				print("lo lee")
			except:
				print( "No se ha podido acceder al fichero {}.".format( prueba) )
				continue

			message = "{}{}?{}\r\n".format( szasar.Command.Upload, prueba, filesize )
			s.sendall( message.encode( "ascii" ) )
			message = szasar.recvline( s ).decode( "ascii" )
			if iserror( message ):
				continue

			message = "{}\r\n".format( szasar.Command.Upload2 )
			s.sendall( message.encode( "ascii" ) )
			s.sendall( filedata )
			message = szasar.recvline( s ).decode( "ascii" )
			if not iserror( message ):
				print( "El fichero {} se ha enviado correctamente.".format( prueba ) )
		elif int(option) == Menu.Delete:
			message = "{}{}\r\n".format( szasar.Command.Delete, filename )
			s.sendall( message.encode( "ascii" ) )
			message = szasar.recvline( s ).decode( "ascii" )
			#if not iserror( message ):
				#print( "El fichero {} se ha borrado correctamente.".format( filename ) )
		elif int(option) == Menu.Modify:
			try:
				prueba = os.path.join(path,filename)
				filesize = os.path.getsize(prueba)
				with open(prueba, "rb" ) as f:
					filedata = f.read()
				print("lo lee")
			except:
				print( "No se ha podido acceder al fichero {}.".format( prueba) )
				continue

			message = "{}{}?{}\r\n".format( szasar.Command.Modify, prueba, filesize )
			s.sendall( message.encode( "ascii" ) )
			message = szasar.recvline( s ).decode( "ascii" )
			if iserror( message ):
				continue

			message = "{}\r\n".format( szasar.Command.Modify2 )
			s.sendall( message.encode( "ascii" ) )
			s.sendall( filedata )
			message = szasar.recvline( s ).decode( "ascii" )
			if not iserror( message ):
				print( "El fichero {} se ha enviado correctamente.".format( prueba ) )
	s.close()
