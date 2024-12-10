# listings/models.py
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

class Inmueble(models.Model):
    TIPOS_INMUEBLE = [
        ('Departamento', 'Departamento'),
        ('Casa', 'Casa'),
        ('Cuarto', 'Cuarto'),
    ]

    DISTANCIAS = [
        ('0-5 km', '0-5 km'),
        ('5-10 km', '5-10 km'),
        ('10-15 km', '10-15 km'),
        ('15-20 km', '15-20 km'),
    ]
    ESTADOS = [
        ('disponible', 'Disponible'),
        ('rentado', 'Rentado')  # Rentado también cubrirá "reservado"
    ]
    estado = models.CharField(max_length=20, choices=ESTADOS, default='disponible')
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inmuebles')
    

    
    tipo_inmueble = models.CharField(max_length=50, choices=TIPOS_INMUEBLE)
    distancia = models.CharField(max_length=50, choices=DISTANCIAS)
    direccion = models.CharField(max_length=255)
    codigo_postal = models.CharField(max_length=10)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    numero_contacto = numero_contacto = models.CharField(max_length=15)
    calificacion = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    arrendador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="arrendados")

    arrendatario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="alquileres")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    


    def __str__(self):
        return f"{self.tipo_inmueble} en {self.direccion}"

class Reserva(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    inmueble = models.ForeignKey('Inmueble', on_delete=models.CASCADE)  # Relación con tu modelo de inmueble
    estado_pago = models.BooleanField(default=False)  # Indica si el pago se completó
    fecha_reserva = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reserva de {self.usuario} para {self.inmueble}"

class ImagenInmueble(models.Model):
    inmueble = models.ForeignKey(Inmueble, related_name='imagenes', on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='inmuebles/imagenes/')


class Calificacion(models.Model):
    inmueble = models.ForeignKey(
        'Inmueble', 
        related_name='calificaciones', 
        on_delete=models.CASCADE
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    estrellas = models.PositiveSmallIntegerField(
        choices=[(i, f"{i} estrellas") for i in range(1, 6)]
    )
    comentario = models.TextField()
    verificado = models.BooleanField(default=False)

    # Opcionales para gestionar tiempos de renta
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    aun_renta = models.BooleanField(default=False)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario} - {self.inmueble} ({self.estrellas} estrellas)"

