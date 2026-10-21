"""Difusion 1D nodal con Dirichlet, Neumann o Robin (guia de difusion).

No calcula un campo 3D. Usa extremos de medio volumen para el balance energetico.
q_salida positivo indica calor que sale; fuente_W_m3 es generacion volumetrica.
"""
import numpy as np


def resolver(longitud, dx, dt, duracion, inicial, izquierda, derecha,
             k=2., rho=2400., cp=900., fuente_W_m3=0., guardar_en=()):
    if not all(np.isfinite(v) for v in (longitud,dx,dt,duracion,k,rho,cp,fuente_W_m3)):
        raise ValueError("Parametros no finitos.")
    if min(longitud,dx,dt,k,rho,cp)<=0 or duracion<0:
        raise ValueError("Parametros positivos; duracion no negativa.")
    n=round(longitud/dx)
    if n<2 or not np.isclose(n*dx,longitud):
        raise ValueError("dx debe dividir longitud.")
    alpha=k/(rho*cp)
    tasa=2*alpha/dx**2
    for b in (izquierda,derecha):
        if b["tipo"] not in ("dirichlet","neumann","robin"):
            raise ValueError("Tipo de borde desconocido.")
        if b["tipo"]=="robin":
            if b["h"]<0: raise ValueError("h no puede ser negativo.")
            tasa=max(tasa,2*alpha/dx**2+2*b["h"]/(rho*cp*dx))
    if dt*tasa>1+1e-12:
        raise ValueError(f"Paso inestable. dt debe ser <= {1/tasa:g} s.")
    x=np.linspace(0,longitud,n+1)
    T=np.asarray(inicial(x) if callable(inicial) else inicial,dtype=float)
    if T.ndim==0: T=np.full(n+1,float(T))
    if T.shape!=x.shape or not np.all(np.isfinite(T)):
        raise ValueError("Condicion inicial incompatible.")
    T=T.copy()
    for indice,b in ((0,izquierda),(-1,derecha)):
        if b["tipo"]=="dirichlet": T[indice]=b["T"]
    pesos=np.ones(n+1)*dx; pesos[[0,-1]]*=.5
    objetivos=sorted(set([0.,float(duracion),*map(float,guardar_en)]))
    if objetivos[0]<0 or objetivos[-1]>duracion:
        raise ValueError("Snapshots fuera del intervalo.")
    perfiles={0.:T.copy()}
    tiempos=[0.]; centro=[float(np.interp(longitud/2,x,T))]
    borde0=[T[0]]; bordeL=[T[-1]]; energia=[float(rho*cp*np.dot(pesos,T))]
    t=0.; siguiente=1
    while t<duracion:
        paso=min(dt,objetivos[siguiente]-t,duracion-t)
        r=alpha*paso/dx**2
        nueva=T.copy()
        # ECUACION DE CALOR: acumulacion = conduccion + fuente.
        nueva[1:-1]=T[1:-1]+r*(T[2:]-2*T[1:-1]+T[:-2])+paso*fuente_W_m3/(rho*cp)
        for indice,vecino,b in ((0,1,izquierda),(-1,-2,derecha)):
            if b["tipo"]=="dirichlet":
                nueva[indice]=b["T"]  # Temperatura impuesta.
            else:
                q=b.get("q_salida",0.) if b["tipo"]=="neumann" else b["h"]*(T[indice]-b["T_ambiente"])
                # NEUMANN/ROBIN: flujo saliente enfria el medio volumen extremo.
                nueva[indice]=T[indice]+2*r*(T[vecino]-T[indice])-2*paso*q/(rho*cp*dx)+paso*fuente_W_m3/(rho*cp)
        T=nueva; t=min(t+paso,duracion)
        tiempos.append(t); centro.append(float(np.interp(longitud/2,x,T)))
        borde0.append(T[0]); bordeL.append(T[-1]); energia.append(float(rho*cp*np.dot(pesos,T)))
        if np.isclose(t,objetivos[siguiente],rtol=0,atol=1e-7):
            perfiles[objetivos[siguiente]]=T.copy(); siguiente+=1
    return {"x":x,"T":T,"perfiles":perfiles,"tiempos":np.array(tiempos),
            "centro":np.array(centro),"borde0":np.array(borde0),"bordeL":np.array(bordeL),
            "energia_J_m2":np.array(energia),"alpha":alpha,"Fo":alpha*dt/dx**2}
