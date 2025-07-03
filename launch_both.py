# Importaciones necesarias de la biblioteca estándar de Python
import subprocess # Para ejecutar y administrar subprocesos
import signal     # Para manejar señales del sistema (como CTRL+C)
import time       # Para introducir pausas (time.sleep)
import sys        # Para acceder a variables y funciones específicas del sistema (como sys.exit, sys.executable)

# Variables globales para almacenar los objetos Popen de los subprocesos.
# Esto permite que el manejador de señales pueda acceder a ellos para terminarlos.
fastapi_process = None
streamlit_process = None

def signal_handler(sig, frame):
    """
    Manejador de señales para SIGINT (generada por CTRL+C).
    Esta función se ejecuta cuando el script recibe la señal SIGINT.
    Su propósito es terminar de forma limpia los subprocesos iniciados.
    """
    print("\nDetectado CTRL+C. Iniciando secuencia de apagado de los servidores...")
    
    global fastapi_process, streamlit_process # Necesario para modificar las variables globales
    
    # Terminar el proceso de Streamlit primero (o el orden que se prefiera)
    if streamlit_process and streamlit_process.poll() is None: # Comprobar si el proceso existe y sigue en ejecución
        print("Terminando el proceso de Streamlit...")
        streamlit_process.terminate() # Envía la señal SIGTERM, solicitando una terminación amigable.
        try:
            # Esperar un tiempo limitado para que el proceso termine por sí mismo.
            streamlit_process.wait(timeout=5) # Espera 5 segundos.
            print("Proceso de Streamlit terminado correctamente.")
        except subprocess.TimeoutExpired:
            # Si el proceso no termina después del timeout, se fuerza la terminación.
            print("El proceso de Streamlit no respondió a SIGTERM, forzando terminación (SIGKILL)...")
            streamlit_process.kill() # Envía la señal SIGKILL, que termina el proceso inmediatamente.
            print("Proceso de Streamlit terminado forzosamente.")
        
    # Terminar el proceso de FastAPI
    if fastapi_process and fastapi_process.poll() is None: # Comprobar si el proceso existe y sigue en ejecución
        print("Terminando el proceso de FastAPI...")
        fastapi_process.terminate() # Envía SIGTERM
        try:
            fastapi_process.wait(timeout=5) # Espera 5 segundos.
            print("Proceso de FastAPI terminado correctamente.")
        except subprocess.TimeoutExpired:
            print("El proceso de FastAPI no respondió a SIGTERM, forzando terminación (SIGKILL)...")
            fastapi_process.kill() # Envía SIGKILL
            print("Proceso de FastAPI terminado forzosamente.")
        
    print("Todos los procesos han sido detenidos. Saliendo del script principal.")
    sys.exit(0) # Salir del script principal con un código de éxito.

# El bloque principal del script, se ejecuta solo si el archivo es ejecutado directamente.
if __name__ == "__main__":
    # Registrar la función signal_handler para que se ejecute cuando se reciba la señal SIGINT.
    signal.signal(signal.SIGINT, signal_handler)

    print("Iniciando el servidor FastAPI en segundo plano...")
    try:
        # Iniciar el script launch_fastapi.py.
        # Se utiliza sys.executable para asegurar que se usa el mismo intérprete de Python
        # que está ejecutando este script principal. Esto es una buena práctica.
        # subprocess.Popen ejecuta el comando en un nuevo proceso, sin bloquear el actual.
        fastapi_process = subprocess.Popen([sys.executable, "launch_fastapi.py"])
        print(f"Servidor FastAPI iniciado. PID: {fastapi_process.pid}")
    except FileNotFoundError:
        print("Error: El archivo 'launch_fastapi.py' no se encontró en el directorio actual.")
        print("Por favor, asegúrate de que el archivo existe y tiene permisos de ejecución si es necesario.")
        sys.exit(1) # Salir con código de error si el script no se encuentra.
    except Exception as e:
        print(f"Se produjo un error inesperado al iniciar FastAPI: {e}")
        sys.exit(1)

    print("Iniciando la aplicación Streamlit en segundo plano...")
    try:
        # Iniciar el script launch_streamlit.py.
        streamlit_process = subprocess.Popen([sys.executable, "launch_streamlit.py"])
        print(f"Aplicación Streamlit iniciada. PID: {streamlit_process.pid}")
    except FileNotFoundError:
        print("Error: El archivo 'launch_streamlit.py' no se encontró en el directorio actual.")
        print("Por favor, asegúrate de que el archivo existe y tiene permisos de ejecución si es necesario.")
        # Si FastAPI ya se inició y Streamlit falla, es buena idea detener FastAPI.
        if fastapi_process and fastapi_process.poll() is None:
            print("Terminando el proceso de FastAPI debido a un error al iniciar Streamlit...")
            fastapi_process.terminate()
            fastapi_process.wait()
        sys.exit(1) # Salir con código de error.
    except Exception as e:
        print(f"Se produjo un error inesperado al iniciar Streamlit: {e}")
        if fastapi_process and fastapi_process.poll() is None:
            print("Terminando el proceso de FastAPI debido a un error al iniciar Streamlit...")
            fastapi_process.terminate()
            fastapi_process.wait()
        sys.exit(1)

    print("\nAmbos scripts han sido iniciados en procesos separados.")
    print("Los servidores deberían estar ejecutándose en paralelo.")
    print("Presiona CTRL+C en esta terminal para detener ambos servidores de forma controlada.")

    # Bucle principal para mantener el script en ejecución y monitorear los subprocesos.
    # El script principal necesita seguir ejecutándose para que los subprocesos no se vuelvan huérfanos
    # y para que el manejador de señales SIGINT siga activo.
    try:
        while True:
            # Comprobar el estado de los subprocesos.
            # El método poll() devuelve el código de salida del proceso si ha terminado, o None si sigue en ejecución.
            fastapi_status = fastapi_process.poll() if fastapi_process else -1 # Usar -1 si no se pudo iniciar
            streamlit_status = streamlit_process.poll() if streamlit_process else -1

            if fastapi_status is not None and fastapi_status != -1:
                print(f"El proceso de FastAPI ha terminado inesperadamente con código de salida: {fastapi_status}.")
                # Si un proceso termina, es buena práctica terminar el otro también.
                if streamlit_process and streamlit_process.poll() is None:
                     print("Terminando el proceso de Streamlit...")
                     streamlit_process.terminate()
                     streamlit_process.wait()
                break # Salir del bucle while
            
            if streamlit_status is not None and streamlit_status != -1:
                print(f"El proceso de Streamlit ha terminado inesperadamente con código de salida: {streamlit_status}.")
                if fastapi_process and fastapi_process.poll() is None:
                    print("Terminando el proceso de FastAPI...")
                    fastapi_process.terminate()
                    fastapi_process.wait()
                break # Salir del bucle while
            
            # Si ambos procesos han terminado por alguna razón (no por CTRL+C, que llama a sys.exit).
            if (fastapi_status is not None and fastapi_status != -1) and \
               (streamlit_status is not None and streamlit_status != -1):
                print("Ambos subprocesos han terminado por su cuenta.")
                break

            time.sleep(1) # Pausa de 1 segundo para reducir el uso de CPU del bucle.
                          # El manejo de CTRL+C es asíncrono gracias a signal, por lo que no se bloquea.
    except KeyboardInterrupt:
        # Este bloque se ejecutaría si SIGINT no estuviera manejado por signal_handler,
        # o si ocurriera un KeyboardInterrupt dentro del propio signal_handler (poco probable).
        # Dado que tenemos un manejador, este bloque es más una salvaguarda.
        print("KeyboardInterrupt recibido en el bucle principal (esto no debería ocurrir si el manejador de señales funciona).")
        signal_handler(signal.SIGINT, None) # Llamar manualmente al manejador.
    finally:
        # Este bloque finally se ejecuta siempre, ya sea que el bucle termine normalmente,
        # por una excepción, o por sys.exit() llamado desde signal_handler.
        # Asegura una limpieza final si algo no fue manejado por signal_handler.
        print("Ejecutando bloque finally del script principal...")
        if fastapi_process and fastapi_process.poll() is None:
            print("Asegurando que el proceso FastAPI esté terminado (desde finally)...")
            fastapi_process.terminate()
            fastapi_process.wait()
        if streamlit_process and streamlit_process.poll() is None:
            print("Asegurando que el proceso Streamlit esté terminado (desde finally)...")
            streamlit_process.terminate()
            streamlit_process.wait()
        print("Script principal finalizado.")
