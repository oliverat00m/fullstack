from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import json
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd

from ..report.ZOS import (
        rdp_method,
        process_experiment,
        find_linear_zone_with_rdp_curve,
        find_extremes_index_linear_zone,
        apply_ransac,
        cut_tail_curve,
        cut_constant_initial_zone
)

from applications.historic.models import Experiments, Measurements, Analysis
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, pool, cast, String
from django.conf import settings
import io

# ---------------------------------------------------------------------------- #
#                                     Rutas                                    #
# ---------------------------------------------------------------------------- #
font_path = "static/fonts/"
# ---------------------------------------------------------------------------- #
#                                    Fuentes                                   #
# ---------------------------------------------------------------------------- #
quicksand_bold = fm.FontProperties(fname=f"{font_path}/Quicksand-Bold.ttf")
quicksand_semi_bold = fm.FontProperties(fname=f"{font_path}/Quicksand-SemiBold.ttf")
quicksand_medium = fm.FontProperties(fname=f"{font_path}/Quicksand-Medium.ttf")
# ---------------------------------------------------------------------------- #
#                                    Colors                                    #
# ---------------------------------------------------------------------------- #
purple_IT = "#9930f7"
red_IT = "#c33c54" 
black_IT = "#45405a"

engine = create_engine('postgresql' + '://' +
                       settings.DATABASES['default']['USER'] + ':' +
                       settings.DATABASES['default']['PASSWORD'] + '@' +
                       settings.DATABASES['default']['HOST'] + '/' +
                       settings.DATABASES['default']['NAME'], 
                        echo=True,
                        poolclass=pool.QueuePool,
                        pool_size=20,
                        max_overflow=1)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def printc(text):
    "Función que imprime un texto por consola en color amarillo"
    print('\033[93m' + text + '\033[0m')



def delete_experiment(experiment_inst):
    pass
    # try:
    #     db = SessionLocal()
    #     experiment = db.query(Experiments).filter(Experiments.nombre_inst == experiment_inst).first()
    #     printc(" if experiment is None:")
    #     if experiment is None:
    #         raise ValueError(f"Experiment with nombre {experiment_inst.id} not found in the database")
    #     measurements = experiment.children  # Recupera las mediciones asociadas al experimento
    #     for measurement in measurements:
    #         db.delete(measurement)  # Elimina la medición actual
    #     db.delete(experiment)  # Elimina el experimento recuperado
    #     db.commit()  # Confirma los cambios en la base de datos
    # finally:
    #     db.close()


def isDay(fecha, dias_seleccionados):
    fecha_datetime = datetime.strptime(fecha, '%d-%m-%Y')
    fecha_dia = fecha_datetime.strftime('%A').lower()
    return fecha_dia in dias_seleccionados


def historic(request):
    # Delete a file
    if request.GET.get("delete"):
        delete_experiment(request.GET.get("nombre_inst"))
        
    try:
        db = SessionLocal()
        experiments = db.query(Experiments).order_by(Experiments.id.desc()).all()
        operadores = set()
        for exp in experiments:
            operadores.add(exp.operador)
        if experiments is None: # Jaime: Se me ocurre acá colocar un experiments = []
            raise ValueError(f"No se encontraron experimentos en la Base de Datos")
    finally:
        db.close()
    
    if request.POST.get("filter"):
        if request.POST.get("date_start") and request.POST.get("date_end"):
            date_start = request.POST.get("date_start")
            date_start = datetime.strptime(date_start, "%Y-%m-%d")
            date_end = request.POST.get("date_end")
            date_end  = datetime.strptime(date_end, "%Y-%m-%d")
            experiments = db.query(Experiments).filter(cast(Experiments.nombre_inst, String) >= date_start.strftime("%Y-%m-%d_%H-%M-%S")).filter(Experiments.nombre_inst <= date_end.strftime("%Y-%m-%d_%H-%M-%S")).all()
            experiments = (
                db.query(Experiments)
                .filter(cast(Experiments.nombre_inst, String) >= date_start.strftime("%Y-%m-%d_%H-%M-%S"))
                .filter(cast(Experiments.nombre_inst, String) <= date_end.strftime("%Y-%m-%d_%H-%M-%S"))
                .all()
            )
        if request.POST.get("days"):
            days_selected = request.POST.getlist("days")
            #queda pendiente filtro
            # experiments = db.query(Experiments).filter(Experiments.nombre_inst.in_(days_selected)).all()
            
        if request.POST.get("selected_elements"):
            operator = request.POST.getlist("selected_elements")
            experiments = db.query(Experiments).filter(Experiments.operador.in_(operator)).all()
            
    for exp in experiments:
        date_time = exp.nombre_inst.split('_')
        exp.date = datetime.strptime(date_time[0], '%Y-%m-%d').strftime('%d-%m-%Y')
        exp.time = datetime.strptime(date_time[1], '%H-%M-%S').time().strftime('%H:%M')

    ###
    pages = []
    page = []
    n_files = len(experiments)
    row_per_page = 7
    n_rows = row_per_page
    n_page = 1

    for exp in experiments:
        n_files -= 1
        page.append(exp)
        n_rows -= 1
        if n_rows == 0 or n_files == 0:
            n_rows = row_per_page
            pages.append({
                # "rows":page,
                "rows2":page,
                "n_page":n_page,
                "state":"hidden" if n_page>1 else ""
                })
            page = []
            if n_files > 0:
                n_page += 1

    context = {
        "historic":"historic",
        "pages":pages,
        "pagination": [i+1 for i in range(n_page)],
        "operadores":list(operadores)
    }
    return render(request,"historic/historic.html",context)

def get_time_string(seconds):
    def format_time(value):
        value = int(value)
        if value>=0 and value<=9:
            return f"0{value}"
        elif value>9:
            return f"{value}"
    hours = format_time(seconds // 3600)
    minutes = format_time((seconds % 3600) // 60)
    seconds = format_time(seconds % 60)
    return f"{hours}:{minutes}:{seconds}"


def calcule_analysis_fields(time, height):
    import numpy as np
    time_original = np.array(time)
    height_original = np.array(height)
    time_rectified, height_rectified = process_experiment(
        time_original, height_original,
        interp_linear=True, interp_seconds=1,
        moving_average=True, window_radius=2
    )

    eps = 0.95
    time_rdp, height_rdp = rdp_method(time_rectified, height_rectified, eps=eps)
    time_rdp, height_rdp = cut_constant_initial_zone(time_rdp, height_rdp, alpha=0.3, tol_slope=0.1)
    time_rdp, height_rdp = cut_tail_curve(time_rdp, height_rdp, alpha=0.5, tol_tail_slope=0.5)

    left_linear_zone, right_linear_zone = find_linear_zone_with_rdp_curve(time_rdp, height_rdp, 3)
    left_index, right_index = find_extremes_index_linear_zone(time_original, time_rdp, left_linear_zone, right_linear_zone)
    time_linear_zone = time_original[left_index:right_index+1]
    height_linear_zone = height_original[left_index:right_index+1]
    slope, intercept = apply_ransac(time_linear_zone, height_linear_zone)

    time_linear_left, time_linear_right = time_original[left_index], time_original[right_index]
    
    return slope, intercept, time_linear_left, time_linear_right

def update_instance_field(analysis, slope, intercept, time_linear_left, time_linear_right, which="all"):
    first_analysis = analysis[0]
    if which == "algorithm" or which == "all":
        printc("update algorithm")
        first_analysis.slope_a=slope,
        first_analysis.intercept_a=intercept,
        first_analysis.time_linear_left_a=time_linear_left,
        first_analysis.time_linear_right_a=time_linear_right,
    if which == "manual" or which == "all":
        printc("update manual")
        first_analysis.slope_m=slope,
        first_analysis.intercept_m=intercept,
        first_analysis.time_linear_left_m=time_linear_left,
        first_analysis.time_linear_right_m=time_linear_right,

def plot_zone_curve(time, height, nombre_inst, slope, intercept, time_linear_left, time_linear_right):

    import base64
    import numpy as np
    time_original = np.array(time)/60 # min
    height_original = np.array(height) # mm
    slope = 60*slope # mm/min
    time_linear_left = time_linear_left/60 # min
    time_linear_right = time_linear_right/60 # min
    
    fig = plt.figure(tight_layout=True, figsize=(10, 5.7058), dpi=200)
    ax = fig.add_subplot(1, 1, 1)
    # ------------------------------ Curva original ------------------------------ #
    plt.scatter(time_original, height_original, s=20, marker='.', c=f"{black_IT}", zorder=1)
    # -------------------------------- Zona lineal ------------------------------- #
    tmin = time_linear_left
    tmax = time_linear_right
    plt.axvspan(tmin, tmax, facecolor=f"{red_IT}", alpha=0.3, zorder=0)
    plt.axline(
        xy1=(time_linear_left, slope * time_linear_left + intercept),
        slope=slope, lw=2,
        color=f"{red_IT}",
        alpha=1,
        zorder=2,
        label=f'La velocidad en la zona\n lineal es {abs(slope):.2f} mm/min'
        )
    y_text = min(height_original) + 0.08*(max(height_original) - min(height_original))
    plt.text(0.5*(tmax+tmin), y_text, "Zona lineal", color=f"{red_IT}", fontsize=14, ha='center', va='top', fontproperties=quicksand_bold)
    # ----------------------------- Zona de inducción ---------------------------- #
    plt.axvspan(time_original[0], tmin, facecolor=f"{black_IT}", alpha=0.3, zorder=0)
    y_text = min(height_original) + 0.15*(max(height_original) - min(height_original))
    plt.text(0.5*(time_linear_left+tmin), y_text, "Inducción", color=f"{black_IT}", fontsize=14, ha='center', va='top', fontproperties=quicksand_bold)
    # ---------------------- Zona de transición y compresión --------------------- #
    plt.axvspan(tmax, time_original[-1], facecolor=f"{purple_IT}", alpha=0.3, zorder=0)
    y_text = min(height_original) + 0.015*(max(height_original) - min(height_original))
    plt.text(1.1*tmax, y_text, "Transición y compresión", color=f"{purple_IT}", fontsize=14, ha='left', va='top', fontproperties=quicksand_bold)


    plt.setp(ax.get_yticklabels(), fontsize=13, fontproperties=quicksand_semi_bold)
    plt.setp(ax.get_xticklabels(), fontsize=13, fontproperties=quicksand_semi_bold)

    fecha_hora = nombre_inst.split('_')
    fecha_hora = datetime.strptime(fecha_hora[0], '%Y-%m-%d').strftime('%d/%m/%Y')
    plt.ylabel('Altura (mm)', fontsize=22, fontproperties=quicksand_bold)
    plt.xlabel('Tiempo (min)', fontsize=22, fontproperties=quicksand_bold)
    plt.ylim(bottom=0)
    ax.legend(
    title_fontproperties=quicksand_semi_bold, 
    prop=quicksand_medium,
    # loc="upper center",
    shadow=True, handleheight=2.5
    )
    plt.setp(ax.get_legend().get_texts(), fontsize=18)

    plt.grid(axis='y')
    ax.tick_params(axis='x', labelsize=15)
    ax.tick_params(axis='y', labelsize=15)

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()
    return image_base64

def instance(request):
    # CUANDO SE ACTIVA ESTE expStop????
    # expStop = request.GET.get("expStop",)
    # if expStop:
    #     ### Stop Experiment
    #     response = rq.get(ip_dir+"stop_measurement")
    #     print("SHOW INSTANCE")
    #     response = rq.get(ip_dir+"get_metadata")
    #     experiment_inst = request.GET.get("nombre_inst")
    if False:
        pass
    else:
        ### Desde Historial
        experiment_inst = request.GET.get("nombre_inst")
    db = SessionLocal()
    try:
        experiment = db.query(Experiments).filter(Experiments.nombre_inst == experiment_inst).first()
        if experiment is None:
            raise ValueError(f"Experiment with nombre {experiment_inst} not found in the database")
        measurements_unsorted = experiment.children
        measurements = sorted(measurements_unsorted, key=lambda m: m.time)
        time   = [m.time for m in measurements]
        height = [m.height for m in measurements]
        nombre_inst = experiment.nombre_inst
        analysis = experiment.analysis

        if len(analysis) == 0:
            slope, intercept, time_linear_left, time_linear_right = calcule_analysis_fields(time, height)
            add_analysis = Analysis(
                slope_a=slope,
                intercept_a=intercept,
                time_linear_left_a=time_linear_left,
                time_linear_right_a=time_linear_right,
                slope_m=slope,
                intercept_m=intercept,
                time_linear_left_m=time_linear_left,
                time_linear_right_m=time_linear_right,
            )
            add_analysis.experiment = experiment
            db.add(add_analysis)
            db.commit()

        elif len(analysis) > 0:
            first_analysis = analysis[0]
            slope             = first_analysis.slope_m
            intercept         = first_analysis.intercept_m
            time_linear_left  = first_analysis.time_linear_left_m
            time_linear_right = first_analysis.time_linear_right_m

        image = plot_zone_curve(time, height, nombre_inst, slope, intercept, time_linear_left, time_linear_right)
        
        duration = get_time_string(float(measurements[-1].time))    
        from_page = request.GET.get("from",)
        inferior_limit = "0.0015"

        context = {
            'experiment_name' : experiment.experimento,
            "operator" : experiment.operador,
            "initial_height" : experiment.alturaInicial,
            "duration" : duration,
            "density" : experiment.densidad,
            "dose" : experiment.dosis,
            "flocculant" : experiment.floculante,
            "material" : experiment.material,
            "superior_limit" : experiment.limiteSuperior,
            "inferior_limit" : inferior_limit,
            "comments" : experiment.comentarios,
            "nombre_inst": experiment.nombre_inst,
            "from" : from_page,
            # "alert" : detentionAlert() if from_page == "medition" else None,
            "siv" : f"{abs(60*slope):.2f}",
            "image" : image,
            }
        context[from_page] = from_page

    finally:
        db.close()

    return render(request,"historic/instance.html",context)

def sedimentation_curve(request):
    experiment_inst = request.GET.get("nombre_inst",)
    db = SessionLocal()
    try:
        experiment = db.query(Experiments).filter(Experiments.nombre_inst == experiment_inst).first()
        if experiment is None:
            raise ValueError(f"Experiment with id {experiment_inst} not found in the database")
        measurements_unsorted = experiment.children
        measurements = sorted(measurements_unsorted, key=lambda m: m.time)
        if len(measurements) == 0:
            raise ValueError(f"No measurements found for experiment with id {experiment_inst}")
        data = [(m.time, m.height) for m in measurements]
        dataDf = pd.DataFrame(data, columns=['time', 'height'])
    finally:
        db.close()

    step = 1
    # if len(dataDf)>250: #Tuve que quitárselo por la nueva funcionalidad en velocity_between_boundaries
    #     from math import floor
    #     step = floor(len(dataDf)/250)

    time = dataDf.time[0:-1:step]/60  # convert to minutes.
    time = time.tolist()
    height = dataDf.height[0:-1:step].tolist()
    expJson = [{"x":t,"y":h} for (t,h) in zip(time,height)]
    return JsonResponse(expJson, safe=False)

def velocity_between_boundaries(request):
    experiment_inst = request.GET.get("nombre_inst",)
    startIndex = int(request.GET.get("startIndex",))
    endIndex = int(request.GET.get("endIndex",))
    db = SessionLocal()
    try:
        experiment = db.query(Experiments).filter(Experiments.nombre_inst == experiment_inst).first()
        if experiment is None:
            raise ValueError(f"Experiment with id {experiment_inst} not found in the database")
        measurements_unsorted = experiment.children
        measurements = sorted(measurements_unsorted, key=lambda m: m.time)
        if len(measurements) == 0:
            raise ValueError(f"No measurements found for experiment with id {experiment_inst}")
        data = [(m.time, m.height) for m in measurements]
        dataDf = pd.DataFrame(data, columns=['time', 'height'])
    finally:
        db.close()

    printc(f"({dataDf.time[startIndex]/60:.2f}, {dataDf.time[endIndex]/60:.2f})")
    time = dataDf.time[startIndex:endIndex+1]
    height = dataDf.height[startIndex:endIndex+1]
    try:
        slope, intercept  = apply_ransac(time, height)
        time_linear_left  = dataDf.time[startIndex]
        time_linear_right = dataDf.time[endIndex]
    except:
        slope, intercept  = float(request.GET.get("slope",)), float(request.GET.get("intercept",))
        time_linear_left  = float(request.GET.get("time_linear_left",)) 
        time_linear_right = float(request.GET.get("time_linear_right",))
    parameters = {
        "slope": slope,
        "intercept": intercept,
        "time_linear_left": time_linear_left,
        "time_linear_right": time_linear_right,
    }
    return JsonResponse(parameters, safe=False)

def update_velocity(request):
    db = SessionLocal()
    try:
        nombre_inst = request.GET.get("nombre_inst",)
        slope  = float(request.GET.get("slope",)) 
        intercept = float(request.GET.get("intercept",))
        time_linear_left  = float(request.GET.get("time_linear_left",)) 
        time_linear_right = float(request.GET.get("time_linear_right",))
        experiment = db.query(Experiments).filter(Experiments.nombre_inst == nombre_inst).first()
        measurements_unsorted = experiment.children
        measurements = sorted(measurements_unsorted, key=lambda m: m.time)
        time   = [m.time for m in measurements]
        height = [m.height for m in measurements]
        if experiment is None:
            raise ValueError(f"Experiment with nombre {nombre_inst} not found in the database")
        analysis = experiment.analysis
        update_instance_field(analysis, slope, intercept, time_linear_left, time_linear_right, which="manual")
        db.commit()
        image = plot_zone_curve(time, height, nombre_inst, slope, intercept, time_linear_left, time_linear_right)
        context = {
            "image": image,
        }
    except Exception as e:
        printc(f"{e} in update_velocity")
    finally:
        db.close()

    return JsonResponse(context, safe=False)

def restore_velocity(request):
    db = SessionLocal()
    context = {}
    # try:
    nombre_inst = request.GET.get("nombre_inst",)
    experiment = db.query(Experiments).filter(Experiments.nombre_inst == nombre_inst).first()
    measurements_unsorted = experiment.children
    measurements = sorted(measurements_unsorted, key=lambda m: m.time)
    time   = [m.time for m in measurements]
    height = [m.height for m in measurements]
    analysis = experiment.analysis
    first_analysis = analysis[0]
    slope             = first_analysis.slope_a
    intercept         = first_analysis.intercept_a
    time_linear_left  = first_analysis.time_linear_left_a
    time_linear_right = first_analysis.time_linear_right_a
    update_instance_field(analysis, slope, intercept, time_linear_left, time_linear_right, which="manual")
    db.commit()
    image = plot_zone_curve(time, height, nombre_inst, slope, intercept, time_linear_left, time_linear_right)
    context = {
        "image": image,
    }
    # except Exception as e:
    #     printc(f"{e} in restore_velocity")

    # finally:
    db.close()

    return JsonResponse(context, safe=False)

def download_csv(request):
    experiment_inst = request.GET.get("nombre_inst")
    db = SessionLocal()
    try:
        experiment = db.query(Experiments).filter(Experiments.nombre_inst == experiment_inst).first()
        if experiment is None:
            raise ValueError(f"Experiment with id {experiment_inst} not found in the database")
        measurements_unsorted = experiment.children
        measurements = sorted(measurements_unsorted, key=lambda m: m.time)
        if len(measurements) == 0:
            raise ValueError(f"No measurements found for experiment with id {experiment_inst}")
        data = [(m.time, m.height, m.sensor1, m.sensor2, m.sensor3) for m in measurements]
        df = pd.DataFrame(data, columns=['time', 'height', 'sensor1', 'sensor2', 'sensor3'])
        # Write csv to a string buffer
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=True)
        # Create a response with csv data
        response = HttpResponse(csv_buffer.getvalue(), content_type='text/csv')
        # Set content disposition header to force download
        response['Content-Disposition'] = 'attachment; filename="{}.csv"'.format(experiment.nombre_inst)
        return response
    finally:
        db.close()

def download_json(request):    
    experiment_inst = request.GET.get("nombre_inst")
    db = SessionLocal()
    try:
        experiment = db.query(Experiments).filter(Experiments.nombre_inst == experiment_inst).first()
        if experiment is None:
            raise ValueError(f"Experiment with id {experiment_inst} not found in the database")
        # Create a response with json data
        experiment_dict = {
            "operador": experiment.operador,
            "experimento": experiment.experimento,
            "alturaInicial": experiment.alturaInicial,
            "material": experiment.material,
            "floculante": experiment.floculante,
            "concentracion": experiment.concentracion,
            "unidadConcentracion": experiment.unidadConcentracion,
            "densidad": experiment.densidad,
            "unidadDensidad": experiment.unidadDensidad,
            "dosis": experiment.dosis,
            "unidadDosis": experiment.unidadDosis,
            "ph": experiment.ph,
            "comentarios": experiment.comentarios,
            "expInit": experiment.expInit,
            "nombre_inst": experiment.nombre_inst,
            "limiteSuperior": experiment.limiteSuperior,
            "IT_id": experiment.IT_id
        }
        experiment_json = json.dumps(experiment_dict, indent=4)
        response = HttpResponse(experiment_json, content_type='application/json')
        # Set content disposition header to force download
        response['Content-Disposition'] = 'attachment; filename="{}.json"'.format(experiment.nombre_inst)
        return response
    finally:
        db.close() 

def download_img(request):
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    experiment_inst = request.GET.get("nombre_inst")
    db = SessionLocal()
    try:
        experiment = db.query(Experiments).filter(Experiments.nombre_inst == experiment_inst).first()
        if experiment is None:
            raise ValueError(f"Experiment with id {experiment_inst} not found in the database")
        measurements_unsorted = experiment.children
        measurements = sorted(measurements_unsorted, key=lambda m: m.time)
        if len(measurements) == 0:
            raise ValueError(f"No measurements found for experiment with id {experiment_inst}")
        data = [(m.time, m.height) for m in measurements]
        dataDf = pd.DataFrame(data, columns=['time', 'height'])

        time = dataDf.time
        height = dataDf.height
    finally:
        db.close() 

    fig = plt.figure(figsize=(12, 6), dpi=150)
    ax = fig.add_subplot(1, 1, 1)
    quicksand_bold = fm.FontProperties(fname="static/fonts/static/Quicksand-Bold.ttf")
    quicksand_regular = fm.FontProperties(fname="static/fonts/static/Quicksand-SemiBold.ttf")
    # sns.set_theme(style="dark", palette="colorblind")
    plt.scatter(
            time, height,
            alpha=0.7,
            s=15,
            marker="o",
            c="#9930f7"
    )
    plt.plot(
        time, height, "--",
        linewidth=1.5,
        alpha=0.2,
        c="#9930f7"
    )

    plt.setp(ax.get_yticklabels(), fontsize=11, fontproperties=quicksand_regular)
    plt.setp(ax.get_xticklabels(), fontsize=11, fontproperties=quicksand_regular)

    plt.ylim(bottom=0)
    plt.title("Resultados del experimento", fontsize=17, fontproperties=quicksand_bold)
    plt.ylabel('Altura de la interfaz (mm)', fontsize=13, fontproperties=quicksand_bold)
    plt.xlabel('Tiempo (s)', fontsize=13, fontproperties=quicksand_bold)
    plt.grid()

    img_buffer = io.BytesIO()  # Crea un img_buffer de bytes en memoria
    plt.savefig(img_buffer, format='png')  # Guarda el gráfico en el img_buffer
    img_buffer.seek(0)  # Coloca el cursor del img_buffer al principio
    response = HttpResponse(img_buffer, content_type='image/png')
    response['Content-Disposition'] = 'attachment; filename="{}.png"'.format(experiment.nombre_inst)
    return response
