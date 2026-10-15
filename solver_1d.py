"""Difusion 1D explicita: propiedades constantes, sin fuente, bordes Dirichlet.

Caso de verificacion: T = T_b + A exp(-alpha*pi^2*t/L^2) sin(pi*x/L).
Es un ejercicio numerico, no una simulacion de la fundacion real.
"""
import argparse
from pathlib import Path
import numpy as np


def solucion_exacta(x, t, longitud, alpha, temperatura_borde=20., amplitud=40.):
    return temperatura_borde + amplitud * np.exp(-alpha * (np.pi / longitud)**2 * t) * np.sin(np.pi * x / longitud)


def simular(longitud=1., dx=0.05, dt=600., duracion=86400.,
            k=2., rho=2400., cp=900., temperatura_borde=20., amplitud=40.):
    valores = [longitud, dx, dt, duracion, k, rho, cp, temperatura_borde, amplitud]
    if not all(np.isfinite(v) for v in valores):
        raise ValueError("Todos los parametros deben ser finitos.")
    if min(longitud, dx, dt, k, rho, cp) <= 0 or duracion < 0:
        raise ValueError("L, dx, dt, k, rho y cp deben ser positivos; duracion >= 0.")
    intervalos = round(longitud / dx)
    if intervalos < 2 or not np.isclose(intervalos * dx, longitud, rtol=1e-9, atol=1e-12):
        raise ValueError("dx debe dividir L exactamente y producir al menos dos intervalos.")
    alpha = k / (rho * cp)
    fo = alpha * dt / dx**2
    if fo > 0.5 + 1e-12:
        raise ValueError(f"Esquema inestable: Fo={fo:.6f} > 0.5. Use dt <= {dx**2/(2*alpha):.6f} s.")
    x = np.linspace(0., longitud, intervalos + 1)
    temperatura = solucion_exacta(x, 0., longitud, alpha, temperatura_borde, amplitud)
    temperatura[[0, -1]] = temperatura_borde
    tiempos, centro = [0.], [float(np.interp(longitud/2, x, temperatura))]
    t = 0.
    while t < duracion:
        paso = min(dt, duracion - t)
        fo_paso = alpha * paso / dx**2
        nueva = temperatura.copy()  # Todos los vecinos pertenecen al instante anterior.
        nueva[1:-1] = temperatura[1:-1] + fo_paso * (
            temperatura[2:] - 2 * temperatura[1:-1] + temperatura[:-2])
        nueva[[0, -1]] = temperatura_borde
        temperatura = nueva
        t = min(t + paso, duracion)
        tiempos.append(t)
        centro.append(float(np.interp(longitud/2, x, temperatura)))
    exacta = solucion_exacta(x, t, longitud, alpha, temperatura_borde, amplitud)
    return {"x": x, "temperatura": temperatura, "exacta": exacta,
            "tiempos": np.array(tiempos), "centro": np.array(centro),
            "alpha": alpha, "fo": fo, "error_max": float(np.max(np.abs(temperatura-exacta)))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for nombre, defecto in [("longitud", 1.), ("dx", .05), ("dt", 600.),
                             ("duracion", 86400.), ("k", 2.), ("rho", 2400.), ("cp", 900.)]:
        parser.add_argument(f"--{nombre}", type=float, default=defecto)
    parser.add_argument("--salida", type=Path, default=Path("resultados/base"))
    args = parser.parse_args()
    parametros = vars(args).copy()
    salida = parametros.pop("salida")
    try:
        resultado = simular(**parametros)
    except ValueError as error:
        parser.error(str(error))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    salida.mkdir(parents=True, exist_ok=True)
    np.savetxt(salida / "perfil.csv", np.column_stack([
        resultado["x"], resultado["temperatura"], resultado["exacta"]]),
        delimiter=",", header="x_m,T_numerica_C,T_exacta_C", comments="")
    np.savetxt(salida / "centro.csv", np.column_stack([
        resultado["tiempos"], resultado["centro"]]), delimiter=",",
        header="tiempo_s,T_centro_C", comments="")
    fig, ejes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    ejes[0].plot(resultado["x"], resultado["temperatura"], "o-", label="Numerica")
    ejes[0].plot(resultado["x"], resultado["exacta"], "--", label="Exacta")
    ejes[0].set(xlabel="Posicion [m]", ylabel="Temperatura [°C]", title="Perfil final")
    ejes[0].legend()
    ejes[1].plot(resultado["tiempos"]/3600, resultado["centro"])
    ejes[1].set(xlabel="Tiempo [h]", ylabel="Temperatura [°C]", title="Centro del dominio")
    for eje in ejes:
        eje.grid(alpha=.3)
    fig.savefig(salida / "temperaturas.png", dpi=160)
    plt.close(fig)
    resumen = (f"alpha = {resultado['alpha']:.8g} m2/s\nFo = {resultado['fo']:.6f} (limite 0.5)\n"
               f"Nodos = {len(resultado['x'])}\nPasos = {len(resultado['tiempos'])-1}\n"
               f"Error maximo final = {resultado['error_max']:.8g} °C\n")
    (salida / "resumen.txt").write_text(resumen, encoding="utf-8")
    print(resumen + f"Resultados: {salida.resolve()}")


if __name__ == "__main__":
    main()
