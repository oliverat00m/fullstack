from django.db import models

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Experiments(Base):
   __tablename__ = "experiments"

   id = Column(Integer, primary_key=True, index=True)
   operador = Column(String)
   experimento = Column(String)
   alturaInicial = Column(Integer)
   material = Column(String)
   floculante = Column(String, nullable=True)
   concentracion = Column(Float, nullable=True)
   unidadConcentracion = Column(String, nullable=True)
   dosis = Column(Float, nullable=True)
   unidadDosis = Column(String, nullable=True)
   densidad = Column(Float, nullable=True)
   unidadDensidad = Column(String, nullable=True)
   ph = Column(Float, nullable=True)
   comentarios = Column(String, nullable=True)
   expInit = Column(Boolean)
   nombre_inst = Column(String)
   limiteSuperior = Column(Integer)
   IT_id = Column(String)

class Measurements(Base):
   __tablename__ = "measurements"

   id = Column(Integer, primary_key=True, index=True)
   time = Column(Float)
   height = Column(Float)
   sensor1 = Column(Float, nullable=True)
   sensor2 = Column(Float, nullable=True)
   sensor3 = Column(Float, nullable=True)
   experiment_id = Column(Integer, ForeignKey("experiments.id"))
   experiment = relationship(Experiments, backref='children')

class Analysis(Base):
   __tablename__ = "analysis"

   id = Column(Integer, primary_key=True, index=True)
   slope_a = Column(Float, nullable=True)               # [mm/seg]
   intercept_a = Column(Float, nullable=True)           # [mm]
   time_linear_left_a = Column(Float, nullable=True)    # [seg]
   time_linear_right_a = Column(Float, nullable=True)   # [seg]
   slope_m = Column(Float, nullable=True)               # [mm/seg]
   intercept_m = Column(Float, nullable=True)           # [mm]
   time_linear_left_m = Column(Float, nullable=True)    # [seg]
   time_linear_right_m = Column(Float, nullable=True)   # [seg]
   experiment_id = Column(Integer, ForeignKey("experiments.id"))
   experiment = relationship(Experiments, backref='analysis')