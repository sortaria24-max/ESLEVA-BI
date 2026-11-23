"""
Generador de datos sintéticos de Estampaciones Levante S.A. (ESLEVA)
====================================================================

Crea todas las fuentes de datos del proyecto de BI:

* ERP (PostgreSQL):  datos/sql/01_crear_tablas.sql y datos/sql/02_cargar_datos.sql
* Calidad (Excel):   datos/excel/calidad_ESLEVA.xlsx  (hojas «inspecciones» y «reclamaciones»)
* Finanzas (Excel):  datos/excel/presupuesto_ESLEVA.xlsx
* MES (CSV):         datos/mes/mes_AAAA_MM.csv  (un fichero por mes)

Los datos son ficticios, pero siguen reglas de negocio para que su análisis
tenga sentido: coherencia entre fuentes, estacionalidad del sector, tendencias,
eventos singulares y errores intencionados en los ficheros de registro manual.

Uso (desde la carpeta raíz del repositorio):

    pip install -r generador/requirements.txt
    python generador/generar_datos_ESLEVA.py

La semilla es fija, así que cada ejecución produce exactamente los mismos datos.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

# ---------------------------------------------------------------------------
# 0. Configuración general
# ---------------------------------------------------------------------------

SEMILLA = 20241992
rng = np.random.default_rng(SEMILLA)
fake = Faker("es_ES")
Faker.seed(SEMILLA)

FECHA_INICIO = dt.date(2024, 1, 1)
FECHA_FIN = dt.date(2026, 10, 31)          # último día con datos
FACTURACION_ANUAL = 38_000_000             # € aproximados en 2024
CALIBRACION = 1.55                         # ajusta la demanda para alcanzar la facturación objetivo

RAIZ = Path(__file__).resolve().parents[1]
DIR_SQL = RAIZ / "datos" / "sql"
DIR_EXCEL = RAIZ / "datos" / "excel"
DIR_MES = RAIZ / "datos" / "mes"

# Eventos singulares del periodo
AVERIA_MAQUINA = 3                                     # PR-03, prensa de alto tonelaje
AVERIA_TOTAL = (dt.date(2025, 3, 10), dt.date(2025, 3, 28))
AVERIA_PARCIAL = (dt.date(2025, 3, 31), dt.date(2025, 4, 4))
INCIDENCIA_MAQUINA = 2                                 # PR-02, prensa progresiva
INCIDENCIA_CALIDAD = (dt.date(2025, 10, 6), dt.date(2025, 11, 14))
INCIDENCIA_CLIENTE = 1                                 # principal cliente

# Estacionalidad mensual de la demanda (agosto: vacaciones de los fabricantes)
ESTACIONALIDAD = {1: 0.95, 2: 1.00, 3: 1.05, 4: 1.00, 5: 1.05, 6: 1.05,
                  7: 1.00, 8: 0.45, 9: 1.05, 10: 1.05, 11: 1.05, 12: 0.75}

# Festivos nacionales y paradas de planta (sin producción)
FESTIVOS = {(1, 1), (1, 6), (5, 1), (8, 15), (10, 12), (11, 1), (12, 6), (12, 8), (12, 25)}

TURNOS = ["Mañana", "Tarde", "Noche"]
MINUTOS_TURNO = 480


def es_parada_planta(d: dt.date) -> bool:
    """Vacaciones de agosto (1-21) y segunda quincena de diciembre (desde el 22)."""
    return (d.month == 8 and d.day <= 21) or (d.month == 12 and d.day >= 22)


def es_laborable(d: dt.date) -> bool:
    return d.weekday() < 5 and (d.month, d.day) not in FESTIVOS


def en(d: dt.date, periodo: tuple[dt.date, dt.date]) -> bool:
    return periodo[0] <= d <= periodo[1]


DIAS = [FECHA_INICIO + dt.timedelta(days=i) for i in range((FECHA_FIN - FECHA_INICIO).days + 1)]
DIAS_LABORABLES = [d for d in DIAS if es_laborable(d)]


# ---------------------------------------------------------------------------
# 1. Tablas maestras
# ---------------------------------------------------------------------------

def crear_familias() -> pd.DataFrame:
    return pd.DataFrame({
        "id_familia": [1, 2, 3, 4, 5],
        "nombre": ["Refuerzos estructurales", "Soportes de motor y transmisión",
                   "Anclajes y piezas de asiento", "Piezas de chasis", "Subconjuntos soldados"],
    })


def crear_maquinas() -> pd.DataFrame:
    # La cadencia teórica se calcula más adelante a partir de la carga real.
    return pd.DataFrame({
        "id_maquina": [1, 2, 3, 4, 5],
        "codigo": ["PR-01", "PR-02", "PR-03", "SL-01", "SL-02"],
        "descripcion": ["Prensa transfer 800 t", "Prensa progresiva 400 t",
                        "Prensa de alto tonelaje 1600 t",
                        "Célula de soldadura robotizada 1", "Célula de soldadura robotizada 2"],
        "tipo": ["Prensa", "Prensa", "Prensa", "Soldadura", "Soldadura"],
        "tonelaje": [800, 400, 1600, None, None],
    })


def crear_clientes() -> pd.DataFrame:
    paises = [("España", "Valencia"), ("España", "Almussafes"), ("España", "Zaragoza"),
              ("España", "Vigo"), ("Portugal", "Aveiro"), ("Francia", "Rennes"),
              ("España", "Barcelona"), ("Alemania", "Stuttgart"), ("España", "Pamplona"),
              ("Portugal", "Palmela"), ("Francia", "Sochaux"), ("Alemania", "Wolfsburg")]
    sufijos = {"España": "S.A.", "Portugal": "Lda.", "Francia": "SAS", "Alemania": "GmbH"}
    prefijos = ["Sistemas", "Componentes", "Módulos", "Ensamblajes", "Autosistemas", "Estructuras"]
    tipos = ["Tier 1"] * 12
    tipos[1] = "OEM"   # el segundo cliente es un fabricante de vehículos
    tipos[7] = "OEM"
    filas = []
    for i, (pais, ciudad) in enumerate(paises, start=1):
        apellido = fake.unique.last_name()
        if tipos[i - 1] == "OEM":
            nombre = f"Vehículos {apellido} {sufijos[pais]}"
        else:
            nombre = f"{prefijos[(i - 1) % len(prefijos)]} {apellido} {sufijos[pais]}"
        filas.append({"id_cliente": i, "nombre": nombre, "tipo": tipos[i - 1], "pais": pais,
                      "ciudad": ciudad,
                      "condiciones_pago_dias": int(rng.choice([30, 60, 60, 90]))})
    return pd.DataFrame(filas)


# Peso de cada cliente en la facturación: los 5 primeros suman el 70 %
PESO_CLIENTES = np.array([0.20, 0.16, 0.13, 0.11, 0.10, 0.06, 0.05, 0.05, 0.045, 0.04, 0.03, 0.025])


def crear_proveedores_y_materias() -> tuple[pd.DataFrame, pd.DataFrame]:
    proveedores = pd.DataFrame({
        "id_proveedor": [1, 2, 3, 4, 5],
        "nombre": [f"Aceros {fake.unique.last_name()} S.A.", f"Siderúrgica {fake.unique.last_name()} S.A.",
                   f"Flejes {fake.unique.last_name()} S.L.", f"Aluminios {fake.unique.last_name()} S.A.",
                   f"Metales {fake.unique.last_name()} S.L."],
        "pais": ["España", "España", "España", "España", "Portugal"],
        "plazo_entrega_dias": [10, 14, 7, 21, 18],
    })
    materias = pd.DataFrame({
        "id_materia_prima": [1, 2, 3, 4, 5],
        "nombre": ["Bobina de acero DC04", "Acero de alta resistencia HSLA 420",
                   "Fleje galvanizado DX51D", "Aluminio 5754", "Aluminio 6082"],
        "tipo": ["Acero", "Acero", "Acero", "Aluminio", "Aluminio"],
        "id_proveedor_principal": [1, 2, 3, 4, 4],
        "id_proveedor_alternativo": [2, 1, 1, 5, 5],
    })
    return proveedores, materias


# Familia -> máquinas en las que se fabrica
MAQUINAS_FAMILIA = {1: [3, 1], 2: [1], 3: [2], 4: [3], 5: [4, 5]}


def crear_productos(clientes: pd.DataFrame) -> pd.DataFrame:
    n_previos, n_nuevos = 100, 32          # referencias anteriores a 2024 y lanzadas en el periodo
    n = n_previos + n_nuevos
    familias = rng.choice([1, 2, 3, 4, 5], size=n, p=[0.24, 0.18, 0.22, 0.18, 0.18])
    # Cada cliente recibe referencias en proporción a su peso (mínimo 3)
    reparto = np.maximum(3, np.round(PESO_CLIENTES * n)).astype(int)
    while reparto.sum() > n:
        reparto[np.argmax(reparto)] -= 1
    while reparto.sum() < n:
        reparto[0] += 1
    id_clientes = rng.permutation(np.repeat(clientes["id_cliente"].to_numpy(), reparto))

    filas = []
    for i in range(n):
        nuevo = i >= n_previos
        if nuevo:
            alta = FECHA_INICIO + dt.timedelta(days=int(rng.integers(30, (FECHA_FIN - FECHA_INICIO).days - 60)))
        else:
            alta = dt.date(int(rng.integers(2017, 2024)), int(rng.integers(1, 13)), 1)
        # El aluminio crece en las referencias nuevas (electrificación del vehículo)
        p_alu = 0.6 if nuevo else 0.12
        aluminio = rng.random() < p_alu
        mp = int(rng.choice([4, 5])) if aluminio else int(rng.choice([1, 2, 3], p=[0.45, 0.35, 0.20]))
        fam = int(familias[i])
        peso = float(np.round(rng.uniform(2.0, 7.5) if fam == 5 else rng.uniform(0.25, 3.5), 3))
        precio_kg = 2.80 if aluminio else 0.85
        valor_anadido = rng.uniform(4.0, 9.0) if fam == 5 else rng.uniform(0.6, 3.5)
        coste = round(peso * precio_kg * 1.12 + valor_anadido, 4)
        margen = rng.uniform(0.14, 0.26)
        precio = round(coste / (1 - margen), 4)
        filas.append({
            "id_producto": i + 1,
            "referencia": f"ESL-{fam}{i + 1:03d}",
            "descripcion": f"{crear_familias().loc[fam - 1, 'nombre'].split()[0]} {fake.unique.bothify('??-###').upper()}",
            "id_familia": fam,
            "id_cliente": int(id_clientes[i]),
            "id_maquina": int(rng.choice(MAQUINAS_FAMILIA[fam])),
            "id_materia_prima": mp,
            "material": "Aluminio" if aluminio else "Acero",
            "peso_kg": peso,
            "coste_estandar": coste,
            "precio_venta": precio,
            "fecha_alta": alta,
            "fecha_baja": None,
            "activo": True,
        })
    productos = pd.DataFrame(filas)
    # 12 referencias antiguas se dan de baja durante el periodo (fin de vida del vehículo)
    bajas = rng.choice(np.arange(n_previos), size=12, replace=False)
    for b in bajas:
        productos.loc[b, "fecha_baja"] = FECHA_INICIO + dt.timedelta(days=int(rng.integers(120, 950)))
        productos.loc[b, "activo"] = False
    return productos


# ---------------------------------------------------------------------------
# 2. Ventas: pedidos y líneas de pedido
# ---------------------------------------------------------------------------

def unidades_anuales_base(productos: pd.DataFrame) -> pd.Series:
    """Reparte la facturación de cada cliente entre sus referencias."""
    unidades = pd.Series(0.0, index=productos.index)
    for idc, grupo in productos.groupby("id_cliente"):
        facturacion_cliente = FACTURACION_ANUAL * PESO_CLIENTES[idc - 1]
        cuotas = rng.dirichlet(np.ones(len(grupo)) * 2.0)
        unidades.loc[grupo.index] = facturacion_cliente * cuotas / grupo["precio_venta"].to_numpy()
    return unidades


def factor_tendencia(material: str, d: dt.date) -> float:
    anos = (d - FECHA_INICIO).days / 365.25
    return (1.18 ** anos) if material == "Aluminio" else (0.96 ** anos)


def factor_precio(prod: pd.Series, id_cliente: int, d: dt.date) -> float:
    """Revisiones anuales de precio y descuento tras la incidencia de calidad."""
    f = 1.0
    if prod["material"] == "Acero" and d >= dt.date(2025, 7, 1):
        f *= 1.03                             # repercusión parcial de la subida del acero
    if id_cliente == INCIDENCIA_CLIENTE and d >= dt.date(2026, 1, 1):
        f *= 0.97                             # compensación pactada por la incidencia de calidad
    return f


def crear_ventas(productos: pd.DataFrame, clientes: pd.DataFrame):
    unidades = unidades_anuales_base(productos)
    lunes = pd.date_range(FECHA_INICIO, FECHA_FIN, freq="W-MON").date
    pedidos, lineas = [], []
    id_pedido, id_linea = 1, 1
    for semana in lunes:
        for idc in clientes["id_cliente"]:
            fecha_pedido = semana + dt.timedelta(days=int(rng.integers(0, 3)))
            if fecha_pedido > FECHA_FIN or not es_laborable(fecha_pedido):
                continue
            estado = "Anulado" if rng.random() < 0.02 else "Servido"
            plazo = int(rng.integers(7, 15))
            fecha_solicitada = fecha_pedido + dt.timedelta(days=plazo)
            if fecha_solicitada.weekday() >= 5:
                fecha_solicitada += dt.timedelta(days=7 - fecha_solicitada.weekday())
            prods = productos[(productos["id_cliente"] == idc)
                              & (productos["fecha_alta"] <= fecha_solicitada)
                              & (productos["fecha_baja"].isna()
                                 | (productos["fecha_baja"].fillna(dt.date(2099, 1, 1)) > fecha_solicitada))]
            nuevas_lineas = []
            for idx, p in prods.iterrows():
                if rng.random() < 0.15:          # no todas las referencias se piden cada semana
                    continue
                semanal = unidades[idx] / 50 * ESTACIONALIDAD[fecha_solicitada.month] \
                    * factor_tendencia(p["material"], fecha_solicitada) * CALIBRACION
                cantidad = int(max(50, round(semanal * rng.normal(1.0, 0.12) / 50) * 50))
                precio = round(p["precio_venta"] * factor_precio(p, idc, fecha_solicitada), 4)
                entrega = None
                if estado == "Servido" and fecha_solicitada <= FECHA_FIN:
                    entrega = fecha_solicitada + dt.timedelta(days=retraso_entrega(p, fecha_solicitada))
                    if entrega > FECHA_FIN:
                        entrega = None           # todavía pendiente de servir
                nuevas_lineas.append({"id_linea": id_linea, "id_pedido": id_pedido,
                                      "id_producto": int(p["id_producto"]), "cantidad": cantidad,
                                      "precio_unitario": precio, "fecha_solicitada": fecha_solicitada,
                                      "fecha_entrega_real": entrega})
                id_linea += 1
            if not nuevas_lineas:
                continue
            pedidos.append({"id_pedido": id_pedido, "id_cliente": int(idc),
                            "fecha_pedido": fecha_pedido, "estado": estado})
            lineas.extend(nuevas_lineas)
            id_pedido += 1
    return pd.DataFrame(pedidos), pd.DataFrame(lineas)


def retraso_entrega(p: pd.Series, solicitada: dt.date) -> int:
    """Días de retraso (negativo = entrega anticipada). Objetivo de servicio ~93 %."""
    afectado = p["id_maquina"] == AVERIA_MAQUINA and dt.date(2025, 3, 12) <= solicitada <= dt.date(2025, 4, 25)
    if afectado and rng.random() < 0.65:
        return int(rng.integers(3, 12))
    if rng.random() < 0.07:
        return int(rng.integers(1, 6))
    return -int(rng.choice([0, 0, 0, 1, 2]))


# ---------------------------------------------------------------------------
# 3. Producción: órdenes de fabricación
# ---------------------------------------------------------------------------

def crear_ordenes(lineas: pd.DataFrame, pedidos: pd.DataFrame, productos: pd.DataFrame) -> pd.DataFrame:
    validas = lineas.merge(pedidos[["id_pedido", "estado"]], on="id_pedido")
    validas = validas[validas["estado"] == "Servido"].copy()
    validas["semana_entrega"] = pd.to_datetime(validas["fecha_solicitada"]).dt.to_period("W-SUN").dt.start_time.dt.date
    demanda = validas.groupby(["id_producto", "semana_entrega"], as_index=False)["cantidad"].sum()
    demanda = demanda.merge(productos[["id_producto", "id_maquina"]], on="id_producto")
    filas = []
    for i, r in enumerate(demanda.sort_values(["semana_entrega", "id_producto"]).itertuples(), start=1):
        inicio = r.semana_entrega - dt.timedelta(days=7)       # se fabrica la semana anterior
        if inicio > FECHA_FIN or inicio < FECHA_INICIO:
            continue
        planificada = int(np.ceil(r.cantidad * 1.02 / 100) * 100)
        rendimiento = min(1.03, rng.normal(0.985, 0.02))
        if r.id_maquina == AVERIA_MAQUINA and dt.date(2025, 3, 3) <= inicio <= dt.date(2025, 3, 31):
            rendimiento *= 0.6                                   # la avería reduce lo fabricado
        fin = inicio + dt.timedelta(days=4)
        estado = "Cerrada" if fin <= FECHA_FIN else "En curso"
        fabricada = int(planificada * rendimiento) if estado == "Cerrada" else int(planificada * rendimiento * 0.5)
        filas.append({"id_of": len(filas) + 1, "id_producto": int(r.id_producto), "id_maquina": int(r.id_maquina),
                      "fecha_inicio": inicio, "fecha_fin": fin, "cantidad_planificada": planificada,
                      "cantidad_fabricada": fabricada, "estado": estado})
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# 4. MES: registros por máquina, día y turno (base del OEE)
# ---------------------------------------------------------------------------

CAUSAS = [  # (causa, tipo, probabilidad por turno, minutos mín., minutos máx.)
    ("Cambio de formato", "Planificada", 0.45, 20, 60),
    ("Mantenimiento preventivo", "Planificada", 0.05, 60, 120),
    ("Avería", "No planificada", 0.08, 30, 180),
    ("Falta de material", "No planificada", 0.03, 20, 90),
    ("Ajustes de calidad", "No planificada", 0.06, 10, 40),
]
TASA_RECHAZO = {1: 0.010, 2: 0.012, 3: 0.014, 4: 0.008, 5: 0.009}


def parada_turno(id_maquina: int, d: dt.date) -> tuple[int, str, str]:
    if id_maquina == AVERIA_MAQUINA and en(d, AVERIA_TOTAL):
        return MINUTOS_TURNO, "Avería", "No planificada"
    if id_maquina == AVERIA_MAQUINA and en(d, AVERIA_PARCIAL):
        return int(rng.integers(180, 300)), "Avería", "No planificada"
    r = rng.random()
    acumulado = 0.0
    for causa, tipo, p, mn, mx in CAUSAS:
        acumulado += p
        if r < acumulado:
            return int(rng.integers(mn, mx + 1)), causa, tipo
    return 0, "Sin parada", ""


def crear_mes(ordenes: pd.DataFrame, maquinas: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    registros = []
    for m in maquinas["id_maquina"]:
        for d in DIAS_LABORABLES:
            for t in TURNOS:
                if es_parada_planta(d):
                    registros.append({"fecha": d, "turno": t, "id_maquina": m, "planificado": 0,
                                      "parada": 0, "causa": "Sin actividad", "tipo": "", "perf": 0.0})
                    continue
                parada, causa, tipo = parada_turno(m, d)
                perf = rng.uniform(0.83, 0.95) - (0.03 if t == "Noche" else 0.0)
                registros.append({"fecha": d, "turno": t, "id_maquina": m, "planificado": MINUTOS_TURNO,
                                  "parada": parada, "causa": causa, "tipo": tipo, "perf": perf})
    mes = pd.DataFrame(registros)
    mes["operativo_h"] = (mes["planificado"] - mes["parada"]) / 60
    mes["semana"] = pd.to_datetime(mes["fecha"]).dt.to_period("W-SUN").dt.start_time.dt.date

    # Producción objetivo de cada máquina y semana = lo fabricado en sus órdenes
    objetivo = ordenes.groupby(["id_maquina", "fecha_inicio"])["cantidad_fabricada"].sum()

    # Cadencia teórica (piezas/hora) coherente con la carga real de cada máquina
    cadencias = {}
    for m in maquinas["id_maquina"]:
        horas = mes.loc[(mes["id_maquina"] == m), "operativo_h"].sum()
        total = objetivo.loc[m].sum()
        cadencias[m] = int(round(total / (horas * 0.89) / 10) * 10)
    maquinas["cadencia_teorica"] = maquinas["id_maquina"].map(cadencias)

    mes["piezas_fabricadas"] = 0
    for (m, semana), idx in mes.groupby(["id_maquina", "semana"]).groups.items():
        meta = objetivo.get((m, semana), 0)
        bloque = mes.loc[idx]
        capacidad = cadencias[m] * bloque["operativo_h"] * bloque["perf"]
        if capacidad.sum() <= 0 or meta <= 0:
            continue
        escala = meta / capacidad.sum()
        piezas = np.minimum(capacidad * escala, cadencias[m] * bloque["operativo_h"] * 0.99)
        mes.loc[idx, "piezas_fabricadas"] = np.floor(piezas).astype(int)

    def rechazo(r):
        tasa = TASA_RECHAZO[r.id_maquina]
        if r.id_maquina == INCIDENCIA_MAQUINA and en(r.fecha, INCIDENCIA_CALIDAD):
            tasa = 0.042
        return int(rng.binomial(r.piezas_fabricadas, tasa)) if r.piezas_fabricadas > 0 else 0

    mes["rechazadas"] = [rechazo(r) for r in mes.itertuples()]
    mes["piezas_conformes"] = mes["piezas_fabricadas"] - mes["rechazadas"]
    return mes, maquinas


def exportar_mes(mes: pd.DataFrame, maquinas: pd.DataFrame) -> None:
    codigos = maquinas.set_index("id_maquina")["codigo"]
    cad = maquinas.set_index("id_maquina")["cadencia_teorica"]
    salida = pd.DataFrame({
        "fecha": pd.to_datetime(mes["fecha"]).dt.strftime("%Y-%m-%d"),
        "turno": mes["turno"],
        "maquina": mes["id_maquina"].map(codigos),
        "cadencia_teorica": mes["id_maquina"].map(cad),
        "tiempo_planificado_min": mes["planificado"],
        "tiempo_parada_min": mes["parada"],
        "causa_parada": mes["causa"],
        "tipo_parada": mes["tipo"],
        "piezas_fabricadas": mes["piezas_fabricadas"],
        "piezas_conformes": mes["piezas_conformes"],
    })
    salida["periodo"] = pd.to_datetime(mes["fecha"]).dt.strftime("%Y_%m")
    DIR_MES.mkdir(parents=True, exist_ok=True)
    for f in DIR_MES.glob("mes_*.csv"):
        f.unlink()
    for periodo, bloque in salida.groupby("periodo"):
        bloque = bloque.drop(columns="periodo")
        # Errores intencionados: ~0,5 % de filas duplicadas por exportaciones repetidas
        dup = bloque.sample(frac=0.005, random_state=int(rng.integers(1e9)))
        bloque = pd.concat([bloque, dup])
        bloque["_t"] = bloque["turno"].map({t: i for i, t in enumerate(TURNOS)})
        bloque = bloque.sort_values(["fecha", "maquina", "_t"], kind="stable").drop(columns="_t")
        bloque.to_csv(DIR_MES / f"mes_{periodo}.csv", sep=";", index=False, encoding="utf-8")


# ---------------------------------------------------------------------------
# 5. Compras de materia prima
# ---------------------------------------------------------------------------

def precio_kg(tipo: str, d: dt.date) -> float:
    meses = (d.year - 2024) * 12 + d.month - 1
    if tipo == "Acero":
        # Estable en 2024, fuerte subida en el primer semestre de 2025 y corrección posterior
        if meses < 12:
            base = 0.82
        elif meses < 17:
            base = 0.82 + (meses - 11) * 0.04
        else:
            base = max(0.92, 1.02 - (meses - 17) * 0.01)
    else:
        base = 2.70 if meses < 12 else (2.95 if meses < 24 else 2.85)
    return round(base * rng.normal(1.0, 0.02), 4)


def crear_compras(ordenes: pd.DataFrame, productos: pd.DataFrame, materias: pd.DataFrame) -> pd.DataFrame:
    o = ordenes.merge(productos[["id_producto", "peso_kg", "id_materia_prima"]], on="id_producto")
    o["kg"] = o["cantidad_fabricada"] * o["peso_kg"] * 1.08        # incluye retales y recortes
    o["mes"] = pd.to_datetime(o["fecha_inicio"]).dt.to_period("M")
    necesidades = o.groupby(["mes", "id_materia_prima"])["kg"].sum()
    filas = []
    for (mes, mp), kg in necesidades.items():
        datos_mp = materias.set_index("id_materia_prima").loc[mp]
        n_entregas = int(rng.integers(2, 5))
        for parte in rng.dirichlet(np.ones(n_entregas) * 3):
            fecha = mes.start_time.date() + dt.timedelta(days=int(rng.integers(0, 25)))
            if fecha > FECHA_FIN:
                continue
            proveedor = int(datos_mp["id_proveedor_principal"] if rng.random() < 0.8
                            else datos_mp["id_proveedor_alternativo"])
            kilos = round(kg * parte / 100) * 100
            if kilos <= 0:
                continue
            p = precio_kg(datos_mp["tipo"], fecha)
            filas.append({"id_compra": 0, "fecha_pedido": fecha,
                          "fecha_recepcion": fecha + dt.timedelta(days=int(rng.integers(5, 22))),
                          "id_proveedor": proveedor, "id_materia_prima": int(mp), "kilos": float(kilos),
                          "precio_kg": p, "importe": round(kilos * p, 2)})
    compras = pd.DataFrame(filas).sort_values(["fecha_pedido", "id_materia_prima"]).reset_index(drop=True)
    compras["id_compra"] = compras.index + 1
    compras.loc[compras["fecha_recepcion"] > FECHA_FIN, "fecha_recepcion"] = None
    return compras


# ---------------------------------------------------------------------------
# 6. Calidad (Excel de registro manual, con errores intencionados)
# ---------------------------------------------------------------------------

VARIANTES_MAQUINA = {"PR-01": ["PR-01", "Prensa 1", "pr-01 ", "PR01"],
                     "PR-02": ["PR-02", "Prensa 2", "pr-02", "PR02 "],
                     "PR-03": ["PR-03", "Prensa 3", " PR-03", "PR03"],
                     "SL-01": ["SL-01", "Soldadura 1", "sl-01", "SL01"],
                     "SL-02": ["SL-02", "Soldadura 2", "SL-02 ", "SL02"]}
VARIANTES_TURNO = {"Mañana": ["Mañana", "mañana", "M"], "Tarde": ["Tarde", "tarde", "T"],
                   "Noche": ["Noche", "NOCHE", "N"]}
DEFECTOS_PRENSA = ["Rebaba", "Grieta", "Cota fuera de tolerancia", "Deformación", "Golpe o arañazo"]
DEFECTOS_SOLDADURA = ["Soldadura incompleta", "Proyecciones", "Cota fuera de tolerancia", "Poro"]


def fecha_sucia(d: dt.date):
    """Mezcla de formatos de fecha, como ocurre en un registro manual."""
    r = rng.random()
    if r < 0.70:
        return dt.datetime(d.year, d.month, d.day)        # fecha real de Excel
    if r < 0.85:
        return d.strftime("%d/%m/%Y")
    if r < 0.95:
        return d.strftime("%Y-%m-%d")
    return f"{d.day}-{d.month}-{str(d.year)[2:]}"


def variante(opciones: list[str]) -> str:
    return opciones[0] if rng.random() < 0.75 else str(rng.choice(opciones[1:]))


def crear_calidad(mes: pd.DataFrame, maquinas: pd.DataFrame, productos: pd.DataFrame,
                  lineas: pd.DataFrame, pedidos: pd.DataFrame, clientes: pd.DataFrame):
    codigos = maquinas.set_index("id_maquina")["codigo"]
    activos = mes[(mes["piezas_fabricadas"] > 0)]
    # Una inspección por máquina y día, en un turno elegido al azar
    muestra = activos.groupby(["id_maquina", "fecha"]).sample(n=1, random_state=SEMILLA)
    insp = []
    for r in muestra.itertuples():
        refs = productos[(productos["id_maquina"] == r.id_maquina) & (productos["fecha_alta"] <= r.fecha)]
        ref = refs.sample(1, random_state=int(rng.integers(1e9))).iloc[0]
        n = int(rng.integers(50, 201))
        tasa = TASA_RECHAZO[r.id_maquina] * 1.2
        if r.id_maquina == INCIDENCIA_MAQUINA and en(r.fecha, INCIDENCIA_CALIDAD):
            tasa = 0.05
        rech = int(rng.binomial(n, tasa))
        defectos = DEFECTOS_SOLDADURA if codigos[r.id_maquina].startswith("SL") else DEFECTOS_PRENSA
        motivo = str(rng.choice(defectos)) if rech > 0 else None
        if rech > 0 and rng.random() < 0.03:
            motivo = None                                   # celda olvidada
        insp.append({"fecha": fecha_sucia(r.fecha), "turno": variante(VARIANTES_TURNO[r.turno]),
                     "maquina": variante(VARIANTES_MAQUINA[codigos[r.id_maquina]]),
                     "referencia": ref["referencia"] if rng.random() > 0.02 else f" {ref['referencia']}",
                     "piezas_inspeccionadas": n if rng.random() > 0.005 else None,
                     "piezas_rechazadas": rech, "motivo_defecto": motivo})
    inspecciones = pd.DataFrame(insp)
    dup = inspecciones.sample(frac=0.01, random_state=SEMILLA)
    inspecciones = pd.concat([inspecciones, dup]).sort_index(kind="stable").reset_index(drop=True)

    # Reclamaciones de cliente
    entregadas = lineas.merge(pedidos, on="id_pedido")
    entregadas = entregadas[entregadas["fecha_entrega_real"].notna()]
    rec = []
    meses = pd.period_range(FECHA_INICIO, FECHA_FIN, freq="M")
    for m in meses:
        n = int(rng.poisson(1.5))
        candidatas = entregadas[pd.to_datetime(entregadas["fecha_entrega_real"]).dt.to_period("M") == m]
        if m.month == 8:
            n = int(rng.poisson(0.5))
        for _ in range(min(n, len(candidatas))):
            rec.append(reclamacion(candidatas.sample(1, random_state=int(rng.integers(1e9))).iloc[0], productos))
    # Incidencia de calidad con el principal cliente (piezas de la PR-02)
    afectadas = entregadas[(entregadas["id_cliente"] == INCIDENCIA_CLIENTE)
                           & entregadas["id_producto"].isin(productos.loc[productos["id_maquina"] == INCIDENCIA_MAQUINA, "id_producto"])
                           & (entregadas["fecha_entrega_real"] >= dt.date(2025, 10, 13))
                           & (entregadas["fecha_entrega_real"] <= dt.date(2025, 11, 28))]
    if afectadas.empty:   # si el cliente no tiene piezas de la PR-02, se usa cualquier cliente con ellas
        afectadas = entregadas[entregadas["id_producto"].isin(productos.loc[productos["id_maquina"] == INCIDENCIA_MAQUINA, "id_producto"])
                               & (entregadas["fecha_entrega_real"] >= dt.date(2025, 10, 13))
                               & (entregadas["fecha_entrega_real"] <= dt.date(2025, 11, 28))]
    for _, l in afectadas.sample(min(9, len(afectadas)), random_state=SEMILLA).iterrows():
        rec.append(reclamacion(l, productos, grave=True))
    reclamaciones = pd.DataFrame(rec).sort_values("_orden").drop(columns="_orden").reset_index(drop=True)

    nombres = clientes.set_index("id_cliente")["nombre"]
    def nombre_sucio(idc):
        n = nombres[idc]
        r = rng.random()
        if r < 0.70:
            return n
        if r < 0.80:
            return n.upper()
        if r < 0.90:
            return n.rsplit(" ", 1)[0]           # sin forma jurídica
        return n + "  "
    reclamaciones["cliente"] = reclamaciones["cliente"].map(nombre_sucio)
    reclamaciones["fecha"] = reclamaciones["fecha"].map(fecha_sucia)
    return inspecciones, reclamaciones


def reclamacion(linea: pd.Series, productos: pd.DataFrame, grave: bool = False) -> dict:
    prod = productos.set_index("id_producto").loc[linea["id_producto"]]
    fecha = linea["fecha_entrega_real"] + dt.timedelta(days=int(rng.integers(3, 20)))
    fecha = min(fecha, FECHA_FIN)
    piezas = int(linea["cantidad"] * (rng.uniform(0.02, 0.10) if grave else rng.uniform(0.002, 0.02)))
    piezas = max(piezas, 5)
    defectos = DEFECTOS_SOLDADURA if prod["id_familia"] == 5 else DEFECTOS_PRENSA
    tipo = "Grieta" if grave else str(rng.choice(defectos))
    coste = round(piezas * prod["precio_venta"] * rng.uniform(2.0, 4.0) + rng.uniform(300, 1500), 2)
    return {"_orden": fecha, "fecha": fecha, "cliente": int(linea["id_cliente"]), "referencia": prod["referencia"],
            "piezas_afectadas": piezas, "tipo_defecto": tipo,
            "coste_eur": coste if rng.random() > 0.05 else None}


# ---------------------------------------------------------------------------
# 7. Presupuesto (Excel de Finanzas, meses en columnas)
# ---------------------------------------------------------------------------

MESES_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def crear_presupuesto(lineas: pd.DataFrame, pedidos: pd.DataFrame, productos: pd.DataFrame,
                      familias: pd.DataFrame) -> pd.DataFrame:
    """Presupuesto elaborado a principio de cada año: real del año anterior + crecimiento objetivo."""
    v = lineas.merge(pedidos, on="id_pedido").merge(productos[["id_producto", "id_familia"]], on="id_producto")
    v = v[v["estado"] == "Servido"]
    v["importe"] = v["cantidad"] * v["precio_unitario"]
    v["ano"] = pd.to_datetime(v["fecha_solicitada"]).dt.year
    base = v[v["ano"] == 2024].groupby("id_familia")["importe"].sum()
    crecimiento = {2024: 1.00, 2025: 1.14, 2026: 1.25}   # el objetivo de 2025-2026 resulta optimista
    peso_mes = np.array([ESTACIONALIDAD[m] for m in range(1, 13)])
    peso_mes = peso_mes / peso_mes.sum()
    filas = []
    for ano in (2024, 2025, 2026):
        for _, f in familias.iterrows():
            anual = base[f["id_familia"]] * crecimiento[ano] * rng.normal(1.0, 0.03)
            ventas = np.round(anual * peso_mes, -2)
            costes = np.round(ventas * (1 - 0.18), -2)
            filas.append([ano, f["nombre"], "Ventas", *ventas])
            filas.append([ano, f["nombre"], "Costes", *costes])
    return pd.DataFrame(filas, columns=["Año", "Familia", "Concepto", *MESES_ES])


# ---------------------------------------------------------------------------
# 7 bis. Portal de previsiones de los clientes (fuente API)
# ---------------------------------------------------------------------------
# Los clientes publican cada lunes en su portal de proveedores la previsión de
# demanda para la semana que comienza cuatro semanas después. ESLEVA la consulta
# a través de una API REST. Se usa un generador aleatorio propio para que añadir
# esta fuente no altere el resto de los datos.

HORIZONTE_SEMANAS = 4
SESGO_CLIENTE = {3: 1.18}        # cliente que sobreestima de forma sistemática su demanda


def crear_previsiones(lineas: pd.DataFrame, pedidos: pd.DataFrame, productos: pd.DataFrame,
                      clientes: pd.DataFrame) -> pd.DataFrame:
    r = np.random.default_rng(SEMILLA + 1)
    v = lineas.merge(pedidos, on="id_pedido").merge(productos[["id_producto", "id_familia"]], on="id_producto")
    v = v[v["estado"] != "Anulado"].copy()
    fs = pd.to_datetime(v["fecha_solicitada"])
    v["semana"] = (fs - pd.to_timedelta(fs.dt.weekday, unit="D")).dt.date
    real = v.groupby(["id_cliente", "id_familia", "semana"])["cantidad"].sum()
    pares = real.reset_index()[["id_cliente", "id_familia"]].drop_duplicates()
    lunes = list(pd.date_range(FECHA_INICIO, FECHA_FIN + dt.timedelta(days=7 * HORIZONTE_SEMANAS),
                               freq="W-MON").date)
    peso = dict(zip(clientes["id_cliente"], PESO_CLIENTES))
    filas, idp = [], 1
    for _, par in pares.sort_values(["id_cliente", "id_familia"]).iterrows():
        idc, idf = int(par["id_cliente"]), int(par["id_familia"])
        serie = real.loc[(idc, idf)]
        sesgo = SESGO_CLIENTE.get(idc, 1 + r.uniform(-0.04, 0.04))
        ruido = 0.08 if peso[idc] >= 0.10 else 0.15        # los clientes pequeños prevén peor
        for semana in lunes:
            emision = semana - dt.timedelta(days=7 * HORIZONTE_SEMANAS)
            if emision < FECHA_INICIO or emision > FECHA_FIN:
                continue
            if semana <= FECHA_FIN:
                base = float(serie.get(semana, 0))
            else:                                          # semanas futuras: media reciente
                base = float(serie[serie.index > FECHA_FIN - dt.timedelta(days=56)].sum()) / 8
            if base == 0 and r.random() < 0.9:
                continue
            if base == 0:                                  # previsión sin pedido posterior
                base = float(serie.mean())
            cantidad = int(max(0, round(base * sesgo * r.normal(1.0, ruido) / 50) * 50))
            filas.append({"id_prevision": idp, "fecha_emision": emision, "semana_entrega": semana,
                          "id_cliente": idc, "id_familia": idf, "cantidad_prevista": cantidad})
            idp += 1
    return pd.DataFrame(filas)


ESQUEMA_PREVISIONES = """-- ============================================================================
-- Portal de previsiones de los clientes - Tabla expuesta mediante API REST
-- Generado automáticamente por generador/generar_datos_ESLEVA.py
-- Ejecutar después de 01_crear_tablas.sql y 02_cargar_datos.sql.
-- Puede ejecutarse varias veces: elimina antes la tabla si ya existe.
-- ============================================================================

BEGIN;

DROP TABLE IF EXISTS previsiones_cliente;

CREATE TABLE previsiones_cliente (
    id_prevision      INTEGER PRIMARY KEY,
    fecha_emision     DATE    NOT NULL,
    semana_entrega    DATE    NOT NULL,
    id_cliente        INTEGER NOT NULL REFERENCES clientes(id_cliente),
    id_familia        INTEGER NOT NULL REFERENCES familias(id_familia),
    cantidad_prevista INTEGER NOT NULL
);
"""


# ---------------------------------------------------------------------------
# 8. Exportación: Excel y SQL
# ---------------------------------------------------------------------------

def exportar_excel(inspecciones, reclamaciones, presupuesto):
    DIR_EXCEL.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(DIR_EXCEL / "calidad_ESLEVA.xlsx", engine="openpyxl",
                        datetime_format="DD/MM/YYYY") as xw:
        inspecciones.to_excel(xw, sheet_name="inspecciones", index=False)
        reclamaciones.to_excel(xw, sheet_name="reclamaciones", index=False)

    # El presupuesto se presenta como lo prepara Finanzas: título, filas en blanco y totales por año
    with pd.ExcelWriter(DIR_EXCEL / "presupuesto_ESLEVA.xlsx", engine="openpyxl") as xw:
        bloques = []
        for ano, g in presupuesto.groupby("Año"):
            bloques.append(g)
            for concepto in ("Ventas", "Costes"):
                tot = g[g["Concepto"] == concepto][MESES_ES].sum()
                bloques.append(pd.DataFrame([[ano, "TOTAL", concepto, *tot]], columns=presupuesto.columns))
        tabla = pd.concat(bloques, ignore_index=True)
        tabla.to_excel(xw, sheet_name="Presupuesto", index=False, startrow=2)
        hoja = xw.sheets["Presupuesto"]
        hoja["A1"] = "ESTAMPACIONES LEVANTE S.A. - Presupuesto de ventas y costes por familia (€)"


ESQUEMA = """-- ============================================================================
-- ERP de Estampaciones Levante S.A. (ESLEVA) - Creación de tablas
-- Generado automáticamente por generador/generar_datos_ESLEVA.py
-- Puede ejecutarse varias veces: elimina antes las tablas si ya existen.
-- Se ejecuta en una única transacción: si falla, no se borra ni se crea nada.
-- ============================================================================

BEGIN;

DROP TABLE IF EXISTS compras, lineas_pedido, pedidos_venta, ordenes_fabricacion,
    productos, materias_primas, proveedores, maquinas, familias, clientes CASCADE;

CREATE TABLE clientes (
    id_cliente            INTEGER PRIMARY KEY,
    nombre                VARCHAR(120) NOT NULL,
    tipo                  VARCHAR(10)  NOT NULL,
    pais                  VARCHAR(40)  NOT NULL,
    ciudad                VARCHAR(60),
    condiciones_pago_dias INTEGER
);

CREATE TABLE familias (
    id_familia INTEGER PRIMARY KEY,
    nombre     VARCHAR(80) NOT NULL
);

CREATE TABLE maquinas (
    id_maquina       INTEGER PRIMARY KEY,
    codigo           VARCHAR(10) NOT NULL UNIQUE,
    descripcion      VARCHAR(80),
    tipo             VARCHAR(20) NOT NULL,
    tonelaje         INTEGER,
    cadencia_teorica INTEGER NOT NULL
);

CREATE TABLE proveedores (
    id_proveedor       INTEGER PRIMARY KEY,
    nombre             VARCHAR(120) NOT NULL,
    pais               VARCHAR(40),
    plazo_entrega_dias INTEGER
);

CREATE TABLE materias_primas (
    id_materia_prima         INTEGER PRIMARY KEY,
    nombre                   VARCHAR(80) NOT NULL,
    tipo                     VARCHAR(20) NOT NULL,
    id_proveedor_principal   INTEGER REFERENCES proveedores(id_proveedor),
    id_proveedor_alternativo INTEGER REFERENCES proveedores(id_proveedor)
);

CREATE TABLE productos (
    id_producto      INTEGER PRIMARY KEY,
    referencia       VARCHAR(20) NOT NULL UNIQUE,
    descripcion      VARCHAR(120),
    id_familia       INTEGER NOT NULL REFERENCES familias(id_familia),
    id_cliente       INTEGER NOT NULL REFERENCES clientes(id_cliente),
    id_maquina       INTEGER NOT NULL REFERENCES maquinas(id_maquina),
    id_materia_prima INTEGER NOT NULL REFERENCES materias_primas(id_materia_prima),
    material         VARCHAR(20) NOT NULL,
    peso_kg          NUMERIC(8,3),
    coste_estandar   NUMERIC(12,4),
    precio_venta     NUMERIC(12,4),
    fecha_alta       DATE,
    fecha_baja       DATE,
    activo           BOOLEAN NOT NULL
);

CREATE TABLE pedidos_venta (
    id_pedido    INTEGER PRIMARY KEY,
    id_cliente   INTEGER NOT NULL REFERENCES clientes(id_cliente),
    fecha_pedido DATE NOT NULL,
    estado       VARCHAR(15) NOT NULL
);

CREATE TABLE lineas_pedido (
    id_linea           INTEGER PRIMARY KEY,
    id_pedido          INTEGER NOT NULL REFERENCES pedidos_venta(id_pedido),
    id_producto        INTEGER NOT NULL REFERENCES productos(id_producto),
    cantidad           INTEGER NOT NULL,
    precio_unitario    NUMERIC(12,4) NOT NULL,
    fecha_solicitada   DATE NOT NULL,
    fecha_entrega_real DATE
);

CREATE TABLE ordenes_fabricacion (
    id_of                INTEGER PRIMARY KEY,
    id_producto          INTEGER NOT NULL REFERENCES productos(id_producto),
    id_maquina           INTEGER NOT NULL REFERENCES maquinas(id_maquina),
    fecha_inicio         DATE NOT NULL,
    fecha_fin            DATE NOT NULL,
    cantidad_planificada INTEGER NOT NULL,
    cantidad_fabricada   INTEGER NOT NULL,
    estado               VARCHAR(15) NOT NULL
);

CREATE TABLE compras (
    id_compra        INTEGER PRIMARY KEY,
    fecha_pedido     DATE NOT NULL,
    fecha_recepcion  DATE,
    id_proveedor     INTEGER NOT NULL REFERENCES proveedores(id_proveedor),
    id_materia_prima INTEGER NOT NULL REFERENCES materias_primas(id_materia_prima),
    kilos            NUMERIC(12,1) NOT NULL,
    precio_kg        NUMERIC(8,4) NOT NULL,
    importe          NUMERIC(14,2) NOT NULL
);

COMMIT;
"""


def valor_sql(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NaT:
        return "NULL"
    if isinstance(v, (bool, np.bool_)):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (dt.date, dt.datetime, pd.Timestamp)):
        return f"'{pd.Timestamp(v).date().isoformat()}'"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        return repr(round(float(v), 4))
    return "'" + str(v).replace("'", "''") + "'"


def inserts(tabla: str, df: pd.DataFrame, lote: int = 1000) -> str:
    cols = ", ".join(df.columns)
    partes = [f"\n-- {tabla}: {len(df)} filas"]
    filas = df.astype(object).where(df.notna(), None).itertuples(index=False, name=None)
    filas = list(filas)
    for i in range(0, len(filas), lote):
        valores = ",\n".join("(" + ", ".join(valor_sql(v) for v in f) + ")" for f in filas[i:i + lote])
        partes.append(f"INSERT INTO {tabla} ({cols}) VALUES\n{valores};")
    return "\n".join(partes)


def exportar_sql(tablas: dict[str, pd.DataFrame]) -> None:
    DIR_SQL.mkdir(parents=True, exist_ok=True)
    (DIR_SQL / "01_crear_tablas.sql").write_text(ESQUEMA, encoding="utf-8")
    cuerpo = ["-- ============================================================================",
              "-- ERP de ESLEVA - Carga de datos (enero 2024 - octubre 2026)",
              "-- Generado automáticamente por generador/generar_datos_ESLEVA.py",
              "-- Ejecutar después de 01_crear_tablas.sql",
              "-- ============================================================================",
              "BEGIN;"]
    for nombre, df in tablas.items():
        cuerpo.append(inserts(nombre, df))
    cuerpo.append("\nCOMMIT;\n")
    (DIR_SQL / "02_cargar_datos.sql").write_text("\n".join(cuerpo), encoding="utf-8")
    exportar_sql_por_partes(tablas)


def exportar_sql_por_partes(tablas: dict[str, pd.DataFrame], max_bytes: int = 250_000) -> None:
    """Divide la carga en ficheros pequeños que pueden pegarse en el SQL Editor de Supabase.

    Cada parte es una transacción independiente y las partes respetan el orden de las
    claves foráneas, por lo que deben ejecutarse en orden numérico.
    """
    dir_partes = DIR_SQL / "carga_por_partes"
    dir_partes.mkdir(parents=True, exist_ok=True)
    for viejo in dir_partes.glob("parte_*.sql"):
        viejo.unlink()
    sentencias = []
    for nombre, df in tablas.items():
        sentencias.extend(s for s in inserts(nombre, df, lote=500).split("\nINSERT INTO ")[1:])
    partes, actual, tam = [], [], 0
    for s in sentencias:
        s = "INSERT INTO " + s
        if actual and tam + len(s.encode()) > max_bytes:
            partes.append(actual)
            actual, tam = [], 0
        actual.append(s)
        tam += len(s.encode())
    partes.append(actual)
    total = len(partes)
    for i, contenido in enumerate(partes, start=1):
        tablas_parte = sorted({c.split(" ", 3)[2] for c in contenido}, key=list(tablas).index)
        cabecera = (f"-- ERP de ESLEVA - Carga de datos, parte {i} de {total}\n"
                    f"-- Tablas: {', '.join(tablas_parte)}\n"
                    "-- Ejecutar en orden, después de 01_crear_tablas.sql\n")
        texto = cabecera + "BEGIN;\n" + "\n".join(contenido) + "\nCOMMIT;\n"
        (dir_partes / f"parte_{i:02d}_de_{total:02d}.sql").write_text(texto, encoding="utf-8")


# ---------------------------------------------------------------------------
# 9. Programa principal
# ---------------------------------------------------------------------------

def main() -> None:
    print("Generando tablas maestras...")
    familias = crear_familias()
    maquinas = crear_maquinas()
    clientes = crear_clientes()
    proveedores, materias = crear_proveedores_y_materias()
    productos = crear_productos(clientes)

    print("Generando ventas...")
    pedidos, lineas = crear_ventas(productos, clientes)

    print("Generando órdenes de fabricación...")
    ordenes = crear_ordenes(lineas, pedidos, productos)

    print("Generando registros del MES...")
    mes, maquinas = crear_mes(ordenes, maquinas)
    exportar_mes(mes, maquinas)

    print("Generando compras...")
    compras = crear_compras(ordenes, productos, materias)

    print("Generando ficheros de Calidad y Presupuesto...")
    inspecciones, reclamaciones = crear_calidad(mes, maquinas, productos, lineas, pedidos, clientes)
    presupuesto = crear_presupuesto(lineas, pedidos, productos, familias)
    exportar_excel(inspecciones, reclamaciones, presupuesto)

    print("Generando scripts SQL...")
    tablas = {"clientes": clientes, "familias": familias, "maquinas": maquinas,
              "proveedores": proveedores, "materias_primas": materias, "productos": productos,
              "pedidos_venta": pedidos, "lineas_pedido": lineas,
              "ordenes_fabricacion": ordenes, "compras": compras}
    exportar_sql(tablas)

    print("Generando previsiones del portal de clientes (API)...")
    previsiones = crear_previsiones(lineas, pedidos, productos, clientes)
    (DIR_SQL / "03_api_previsiones.sql").write_text(
        ESQUEMA_PREVISIONES + inserts("previsiones_cliente", previsiones) + "\n\nCOMMIT;\n", encoding="utf-8")

    print("\nResumen de filas generadas:")
    for nombre, df in tablas.items():
        print(f"  {nombre:<22}{len(df):>8}")
    print(f"  {'MES (registros)':<22}{len(mes):>8}")
    print(f"  {'inspecciones':<22}{len(inspecciones):>8}")
    print(f"  {'reclamaciones':<22}{len(reclamaciones):>8}")
    print(f"  {'previsiones_cliente':<22}{len(previsiones):>8}")


if __name__ == "__main__":
    main()
