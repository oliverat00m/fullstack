from fpdf import FPDF
import numpy as np
import matplotlib.pyplot as plt
import io
# import mplstereonet
def get_intervalo(n,  min, max, intervaloSize):

        pos = int(int(n)/intervaloSize)
        bins = np.arange(min, max, intervaloSize)
        bins = np.append(bins, max-intervaloSize)

        return [str(bins[pos]), str(bins[pos]+intervaloSize)]
def make_RoseDiagrams(strikes, dips, weights, opTerzaghi, figsize=(15, 7)):

    # Calculate the number of directions (strikes) every 10° using
    bin_edges = np.arange(-5, 366, 10)

    if (opTerzaghi == '1'):
        number_of_strikes, bin_edges = np.histogram(
            strikes, bin_edges, weights=weights.to_list())
    else:
        number_of_strikes, bin_edges = np.histogram(strikes, bin_edges)

    # Sum the last value with the first value.
    number_of_strikes[0] += number_of_strikes[-1]

    # Moda Strikes
    binsStrikes = np.arange(0, 380, 20)
    if (opTerzaghi == '1'):
        nStrikes, binsStrikes = np.histogram(
            strikes, binsStrikes, weights=weights.to_list())
    else:
        nStrikes, binsStrikes = np.histogram(strikes, binsStrikes)
    modaStrikes = [binsStrikes[nStrikes.argmax()],
                binsStrikes[nStrikes.argmax()]+20]

    # Sum the first half 0-180° with the second half 180-360° to achieve the "mirrored behavior" of Rose Diagrams.
    half = np.sum(np.split(number_of_strikes[:-1], 2), 0)
    two_halves = np.concatenate([half, half])

    fig = plt.figure(figsize=figsize)

    # Create the rose diagram.
    ax = fig.add_subplot(121, projection='stereonet')

    ax.pole(strikes, dips, c='k', label='Pole of the Planes', markersize=2)

    if (opTerzaghi == '1'):
        ax.density_contourf(strikes, dips, measurement='poles',
                            cmap='Blues', weights=weights.to_list())
    else:
        ax.density_contourf(strikes, dips, measurement='poles', cmap='Blues')

    # print('opTerzaghi: ', opTerzaghi)

    ax.grid()

    ax = fig.add_subplot(122, projection='polar')
    ax.bar(np.deg2rad(np.arange(0, 360, 10)), two_halves,
        width=np.deg2rad(10), bottom=0.0, color='blue', edgecolor='k')
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)

    if two_halves.max() + 1 > 10:
        ax.set_rgrids(np.arange(1, two_halves.max() + 1,
                    int(two_halves.max() / 10)), angle=0, weight='black')
    else:
        ax.set_rgrids(np.arange(1, two_halves.max() + 1, 1),
                    angle=0, weight='black')

    ax.set_thetagrids(np.arange(0, 360, 45), labels=np.arange(0, 360, 45))

    # fig.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()

    return modaStrikes, buf
def make_histogram(strikes, dipdirs, dips, weights, opTerzaghi, figsize=(10, 10)):
    plt.figure(figsize=figsize)
    if (opTerzaghi == '1'):
        (nDipdir, binsDipdir, patches) = plt.subplot(211).hist(x=dipdirs, bins=range(
            0, 380, 20), color='#cdcdcd', rwidth=0.95, weights=weights.to_list())
    else:
        (nDipdir, binsDipdir, patches) = plt.subplot(211).hist(
            x=dipdirs, bins=range(0, 380, 20), color='#cdcdcd', rwidth=0.95)
    plt.title('DIPDIR', fontsize=30)
    plt.ylabel('Frecuencia', fontsize=20)
    plt.xticks(range(0, 380, 20))
    if (opTerzaghi == '1'):
        (nDip, binsDip, patches) = plt.subplot(212).hist(x=dips, bins=range(
            0, 100, 10), color='#cdcdcd', rwidth=0.95, weights=weights.to_list())
    else:
        (nDip, binsDip, patches) = plt.subplot(212).hist(
            x=dips, bins=range(0, 100, 10), color='#cdcdcd', rwidth=0.95)

    plt.title('Dip', fontsize=30)
    plt.ylabel('Frecuencia', fontsize=20)
    plt.xticks(range(0, 100, 10))

    plt.subplots_adjust(left=0.1,
                        bottom=0.1,
                        right=0.9,
                        top=0.9,
                        wspace=0.4,
                        hspace=0.6)
    bufHistogramas = io.BytesIO()
    plt.savefig(bufHistogramas, format='png')

    modaDipdir = [binsDipdir[nDipdir.argmax()],
                binsDipdir[nDipdir.argmax()]+20]
    modaDip = [binsDip[nDip.argmax()], binsDip[nDip.argmax()]+10]
    # plt.savefig('img/histograma.png', format='png')
    return modaDipdir, modaDip, bufHistogramas
    #instead of returning, save the graphs in img folder
def get_data(totalRows, data, opTerzaghi):
    try:
        errorAzimut = data['DIPDIR'].value_counts(dropna=False)['-']
    except:
        errorAzimut = 0
    try:
        errorFrecuencia = data['DIP'].value_counts(dropna=False)['-']

    except:
        errorFrecuencia = 0

    try:
        errorCotas = data['cota'].value_counts(dropna=False)[-1]
    except:
        errorCotas = 0
    eficiencia = (
        (3*totalRows - (errorAzimut + errorFrecuencia+errorCotas)) / (3*totalRows))*100
    eficiencia = round(eficiencia, 2)
    percCotas = round((((totalRows - errorCotas) / totalRows)*100), 2)
    percAzimut = round((((totalRows - errorAzimut) / totalRows)*100), 2)
    percFrecuencia = round(
        (((totalRows - errorFrecuencia) / totalRows)*100), 2)

    data = data[data['DIP'] != "-"]
    data.loc[:, 'DIP'] = data['DIP'].astype('float', errors='ignore')
    data.loc[:, 'DIPDIR'] = data['DIPDIR'].astype('float', errors='ignore')

    # data['DIP'] = data['DIP'].astype('float', errors='ignore')
    # data['DIPDIR'] = data['DIPDIR'].astype('float', errors='ignore')

    #transformación de strikes para que queden entre 0 y
    strikes = np.array([dd-90 if dd-90 >= 0 else dd +
                    270 for dd in data['DIPDIR']])
    # strikes= np.array([dd+90 if dd+90<=360 else dd-270 for dd in data['DIPDIR']])

    modaDipdir, modaDip, bufHistogramas = make_histogram(strikes, data['DIPDIR'].astype(
        int).values, data['DIP'].astype(int).values, data['weight'], opTerzaghi)
    bufHistogramas.seek(0)
    # graficos de polo y diagrama de rosa
    modaStrikes, bufDiagrams = make_RoseDiagrams(
        strikes, data['DIP'].astype(int).values, data['weight'], opTerzaghi)
    bufDiagrams.seek(0)

    maxDipdir = get_intervalo(data['DIPDIR'].max(skipna=True), 0, 360, 20)
    minDipdir = get_intervalo(data['DIPDIR'].min(skipna=True), 0, 360, 20)
    maxDip = get_intervalo(data['DIP'].max(skipna=True), 0, 90, 10)
    minDip = get_intervalo(data['DIP'].min(skipna=True), 0, 90, 10)
    
    return eficiencia, percAzimut, percFrecuencia, percCotas, modaDipdir, modaDip, bufHistogramas, modaStrikes, bufDiagrams, maxDipdir, minDipdir, maxDip, minDip

class create_pdf(FPDF):
    
    def informe(self,diaclasas, fallas, galerias, file, mina, user, rangoCotas, reportType, nombrePlano, opTerzaghi,cotas,cotasmin,cotasmax):
        
        self.set_title("Informe GeoRec")
        #define ancho de las lineas y color negro
        self.set_draw_color(0,0,0) 
        self.set_line_width(0.4)
        
        #agrega fuentes necesarias para el pdf
        self.add_fonts()
        
        #titulo
        self.pdf_title("Informe Levantamiento Estructural")
        
        #tabla datos del informe
        self.metadata(user, opTerzaghi, cotas, cotasmin, cotasmax, nombrePlano)
        
        #tabla diaclasas
        self.data_table(diaclasas, "Diaclasas",opTerzaghi)
        
        #tabla fallas
        self.data_table(fallas, "Fallas",opTerzaghi)
        
    def add_fonts(self):
        self.add_font('NexaRegular', '', "fonts/Nexa Regular.ttf", uni=True)
        self.add_font('NexaBold', '', "fonts/Nexa Bold.ttf", uni=True)
        self.add_font('NexaLight', '', "fonts/Nexa Light.otf", uni=True)
        self.add_font('FuturaMedium', '', "fonts/Futura book font.ttf", uni=True)
        self.add_font('FuturaBold', '', "fonts/Futura medium bold.ttf", uni=True)
    
    def pdf_title(self, title):
        self.add_page()

        self.set_font('NexaBold', '', 30)
        self.set_text_color(0, 0, 0)
        self.set_x(10)
        self.cell(self.w, 20, title, align="L")
        self.ln(2)
     
    def metadata(self, user, opTerzaghi, cotas, cotasmin, cotasmax,nombrePlano):
        #separacion titulo
        self.ln(17)
        metadata_width = self.w - 20

        #guarda la posicion para el titulo del plano
        self.set_font('FuturaBold', '', 12)
        current_x = self.get_x()
        current_y = self.get_y()
        
        #tabla con  metadata
        with self.table(width= metadata_width, col_widths=(1.5, 0.5, 1, 1), line_height=10, first_row_as_headings=False) as table:
            row = table.row()
            row.cell("Plano: ",colspan=2)
            self.set_font('FuturaMedium', '', 12)
            row.cell("void")
            self.set_font('FuturaMedium', '', 8)
            row.cell(f" ( {cotasmax['x']} , {cotasmin['y']} )")
            row.cell(f" ( {cotasmin['x']} , {cotasmin['y']} )")
        
        #se inserta el titulo del plano
        # Se hace así para que esté en formatos distintos (negrita y no-negrita)
        aux_x = self.get_x()
        aux_y = self.get_y()
        self.set_xy(current_x, current_y)
        self.set_font('FuturaMedium', '', 12)
        self.cell(self.get_string_width("Plano: ")+self.get_string_width(nombrePlano)+3, 10, nombrePlano, align="R", border=0)
        self.set_xy(aux_x, aux_y) #vuelvo a la posicion original del puntero (donde debe ir el resto del informe)

        #estilo
        self.set_font('FuturaMedium', '', 10)
        #decido si opTergazhi o no
        if(opTerzaghi):
            estado="Activado"
        else:
            estado="Desactivado"
        
        #tabla con  metadata
        with self.table(width= metadata_width, col_widths=(1.5, 0.5, 1, 1), line_height=10, first_row_as_headings=False, text_align="CENTER" ) as table:
            row = table.row()
            current_x = self.get_x() #se guarda donde debe ir el titulo de cotas
            current_y = self.get_y()
            row.cell(f"\nMin: {cotas[0]}  Máx: {cotas[1]}\n")
            t_current_x = self.get_x() + metadata_width*1.5/4 #y el titulo de Terzaghi
            t_current_y = self.get_y()
            row.cell(f"\n{estado}\n")
        
        #se inserta titulo de cotas    
        aux_y = self.get_y()
        self.set_xy(current_x, current_y)
        self.set_font('FuturaBold', '', 12)
        self.cell(metadata_width*1.5/4, 10, "Cotas", align="C", border=0)
        
        #lo mismo con Terzaghi
        self.set_xy(t_current_x, t_current_y)
        self.cell(metadata_width*0.5/4, 10, "Terzaghi", align="C", border=0)
        
        #se regresa al punto donde se estaba en el informe
        self.set_y(aux_y - 20)
        self.set_x(metadata_width/2 + 10)
        
        #estilos
        self.set_font('FuturaMedium', '', 8)
        
        #resto de datos
        with self.table(width=metadata_width/2,col_widths=(1,1),line_height=10, align="LEFT" , first_row_as_headings=False ) as table:
            row = table.row()
            row.cell(f" ( {cotasmin['x']} , {cotasmax['y']} )")
            row.cell(f" ( {cotasmax['x']} , {cotasmax['y']} )")
            
            row = table.row()
            from datetime import date
            fecha_hoy = date.today().strftime("%d/%m/%Y")
            row.cell(f"Fecha: {fecha_hoy}")
            row.cell(f"Usuario: {user}")
     
    def data_table(self, data, title, opTerzaghi):
        #titulo
        totalRows = len(data.index)
        self.set_font('NexaRegular', '', 15)
        self.cell(self.w - 20, 20, f"{title} ({totalRows} en total)", align="L")
        self.ln(5)
        
        #conseguir datos y graficos
        (eficiencia,
         percAzimut,
         percFrecuencia,
         percCotas,
         modaDipdir,
         modaDip,
         bufHistogramas,
         modaStrikes,
         bufDiagrams,
         maxDipdir,
         minDipdir,
         maxDip,
         minDip) = get_data(totalRows, data, opTerzaghi)
        
        width_aux = (self.w - 20)/5
        width_left = width_aux*2
        width_right = width_aux*3
        
        #estilos tabla
        self.set_font('Times', '', 10)
        self.ln(10)
        #guardar posicion altura
        current_x = self.get_x()
        current_y = self.get_y()
        self.set_font("FuturaMedium", '',11)
        
        #tabla con eficiencia, dipdir, frecuencia, cotas
        with self.table(width=width_left,col_widths=(1,1),line_height=12, align="LEFT", first_row_as_headings=False) as table:
            row = table.row()
            row.cell(f"Eficiencia: {eficiencia}%")
            row.cell(f"Dipdir: {percAzimut}%")
            
            row = table.row()
            row.cell(f"Frecuencia: {percFrecuencia}%")
            row.cell(f"Cotas: {percCotas}%")
            
        
        self.set_y(current_y)
        self.set_x(width_left + 10)
        
        #tabla con datos dip
        with self.table(width=width_right,col_widths=(1,1,1), line_height=6, align="LEFT", text_align="LEFT", first_row_as_headings=False) as table:
            row = table.row()
            row.cell(f"Dip\nMínimo: [{minDip[0]},{minDip[1]}]\nMáximo: [{maxDip[0]},{maxDip[1]}]\nModa: [{modaDip[0]},{modaDip[1]}]")
            row.cell(f"Dip\nMínimo: [{minDip[0]},{minDip[1]}]\nMáximo: [{maxDip[0]},{maxDip[1]}]\nModa: [{modaDip[0]},{modaDip[1]}]")
            row.cell(f"Dip\nMínimo: [{minDip[0]},{minDip[1]}]\nMáximo: [{maxDip[0]},{maxDip[1]}]\nModa: [{modaDip[0]},{modaDip[1]}]")
        
        #Logica para insercion de imagenes y titulos
        current_y = self.get_y()
        current_x = self.get_x()
        self.image(bufHistogramas, w=width_left-5, h=width_left-15)
        self.set_xy(current_x,current_y)
        self.cell(width_left,width_left-15,"",align="C", border=1)
        self.set_xy(width_left + 10, current_y+5)
        current_x = self.get_x()
        self.image(bufDiagrams, w=width_right)
        self.set_xy(current_x,current_y+3)
        self.set_font("FuturaMedium",'',8)
        self.cell(width_right, 0, "Concentración de polos                            Rosetas de rumbo", align="C", border=0)
        self.set_xy(current_x,current_y)
        self.cell(width_right,width_left-15,"",align="C", border=1)
        self.ln(width_left-20)
            
    def header(self):
        self.set_draw_color(0,0,0)
        self.set_line_width(0.4)
        self.set_font('FuturaBold', '', 10)
        self.set_text_color(128, 128, 128)
        self.set_xy(15,10)
        self.cell(0, 10, 'GEOREC | ejemplo', 0, 0, 'L')
        self.set_xy(self.w - 15 - 12, 5)
        # now the logo to the right
        self.image('img/Logo.png', w=12, h=12)
        self.ln(1.5)
        self.set_x(15)
        # now the line
        self.cell(self.w - 30, 0, '', 'T', 2)
    
    
    
    