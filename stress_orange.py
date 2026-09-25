import multiprocessing
import os
import time

# Configuração
LED = "/sys/class/leds/NOME_DO_LED"   # troque pelo nome que aparece em ls /sys/class/leds/
STEP_TIME = 15                      # segundos em cada nível
TEMP_LIMIT = 65                       # parada de segurança (°C)
LEVELS = [10,40,50,100]


#Carga
def burn(level):
    # Trabalha 'level' por cento de cada período de 0,1 s e descansa o resto
    period = 0.1
    busy = period * level / 100
    while True:
        t0 = time.time()
        while time.time() - t0 < busy:
            pass
        time.sleep(period - busy)


def start_load(level, cores):
    processes = []
    for i in range(cores):
        p = multiprocessing.Process(target=burn, args=(level,), daemon=True)
        p.start()
        processes.append(p)
    return processes


def stop_load(processes):
    for p in processes:
        p.terminate()


# temperatura
def read_temp():
    with open("/sys/class/thermal/thermal_zone0/temp") as f:
        return int(f.read()) / 1000


# Led
def led_write(file, value):
    with open(f"{LED}/{file}", "w") as f:
        f.write(value)


def blink(times,deadline):
    for i in range(times):
        if time.time()>= deadline:
            return
        led_write("brightness", "1")
        time.sleep(0.25)
        led_write("brightness", "0")
        time.sleep(0.25)
    time.sleep(max(0, min(1.5, deadline - time.time())))   # pausa para separar um grupo de piscadas do próximo


#Programa principal
if __name__ == "__main__":
    cores = os.cpu_count()

    with open(f"{LED}/trigger") as f:
        old_trigger = f.read().split("[")[1].split("]")[0]
    led_write("trigger", "none")

    print(f"Teste em degraus: {len(LEVELS)} níveis de {STEP_TIME} s em {cores} núcleos")

    processes = []
    too_hot = False
    try:
        for level in LEVELS:
            print(f"--- Nível {level}% ---")
            processes = start_load(level, cores)

            step_start = time.time()
            step_end = step_start + STEP_TIME
            while time.time() < step_end:
                blink(level // 10, step_end)
                temp = read_temp()
                elapsed = int(time.time() - step_start)
                print(f"{level:3d}%  {elapsed:4d}s  temperatura: {temp:.1f}C")
                if temp > TEMP_LIMIT:
                    print("Muito quente, parando teste")
                    too_hot = True
                    break

            stop_load(processes)
            for p in processes:
                p.terminate()
            for p in processes:
                p.join()
            if too_hot:
                break

        if not too_hot:
            print("Todos os níveis concluídos")
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário")
    finally:
        stop_load(processes)
        led_write("brightness", "0")
        led_write("trigger", old_trigger)
        print("Carga encerrada, LED devolvido ao sistema")