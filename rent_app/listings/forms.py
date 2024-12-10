# listings/forms.py
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Inmueble, ImagenInmueble, Calificacion
from listings.models import Calificacion, Reserva
from django.core.exceptions import ValidationError
import re

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(label="Nombre y Apellido", max_length=50, required=True)
    email = forms.EmailField(label="Correo electrónico", max_length=30, required=True)
   

    class Meta:
        model = User
        fields = ("first_name", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Eliminar los textos de ayuda para los campos de contraseña
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None


    def clean_email(self):
        email = self.cleaned_data.get('email')
        pattern = r'^[\w\.-]+@(gmail\.com|hotmail\.com|yahoo\.com)$'
        if not re.match(pattern, email):
            raise ValidationError("El correo electrónico debe ser de un dominio válido como gmail.com, hotmail.com o yahoo.com.")
        if User.objects.filter(email=email).exists():
            raise ValidationError("Este correo electrónico ya está registrado.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.email = self.cleaned_data["email"]

        # Utilizar el email como nombre de usuario único.
        user.username = user.email

        if commit:
            user.save()
        return user


class CustomUserUpdateForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombre y Apellido", max_length=50, required=True)
    email = forms.EmailField(label="Correo electrónico", max_length=30, required=True)

    class Meta:
        model = User
        fields = ("first_name", "email",)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user
class CustomPasswordChangeForm(PasswordChangeForm):
    def save(self, commit=True):
        user = super().save(commit=commit)
        # Actualizar la sesión con el nuevo hash para que el usuario no se cierre sesión
        update_session_auth_hash(self.request, user)
        return user
    
class EmailAuthenticationForm(forms.Form):
    email = forms.EmailField(label="Correo electrónico",max_length=30)
    password = forms.CharField(label="Contraseña", max_length=15, widget=forms.PasswordInput)

    def clean(self):
        email = self.cleaned_data.get("email")
        password = self.cleaned_data.get("password")
        
        # Buscar al usuario por correo electrónico
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise forms.ValidationError("Correo electrónico y/o contraseña incorrectos.")
        
        # Autenticar usando el nombre de usuario del usuario encontrado
        user = authenticate(username=user.username, password=password)
        
        if user is None:
            raise forms.ValidationError("Correo electrónico y/o contraseña incorrectos.")
        
        self.cleaned_data["user"] = user
        return self.cleaned_data
        


class InmuebleForm(forms.ModelForm):
    class Meta:
        model = Inmueble
        fields = ['tipo_inmueble', 'distancia', 'direccion', 'codigo_postal', 'descripcion', 'precio', 'numero_contacto']
        widgets = {
            'tipo_inmueble': forms.Select(attrs={'class': 'form-control'}),
            'distancia': forms.Select(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_postal': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control'},),
            'numero_contacto': forms.TextInput(attrs={'class': 'form-control'},),
        }
       

class AsignarArrendatarioForm(forms.ModelForm):
    arrendatario = forms.ModelChoiceField(queryset=User.objects.all(), required=True, label="Selecciona al arrendatario")

    class Meta:
        model = Inmueble
        fields = ['arrendatario']

class CalificacionForm(forms.ModelForm):
    class Meta:
        model = Calificacion
        fields = ['fecha_inicio', 'fecha_fin', 'aun_renta', 'estrellas', 'comentario']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'placeholder': 'Selecciona la fecha de inicio'
            }),
            'fecha_fin': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'placeholder': 'Selecciona la fecha de fin'
            }),
            'aun_renta': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'style': 'margin-top: 10px;'
            }),
            'estrellas': forms.RadioSelect(choices=[
                (1, '1 estrella'),
                (2, '2 estrellas'),
                (3, '3 estrellas'),
                (4, '4 estrellas'),
                (5, '5 estrellas')
            ], attrs={
                'class': 'form-check-inline'
            }),
            'comentario': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Escribe tu comentario...',
                'style': 'resize: none;'
            }),
        }
        labels = {
            'fecha_inicio': 'Fecha de inicio de renta',
            'fecha_fin': 'Fecha de término de renta',
            'aun_renta': '¿Aún rentas este lugar?',
            'estrellas': 'Valora este inmueble',
            'comentario': 'Agrega un comentario',
        }

    def __init__(self, *args, **kwargs):
        # Captura del usuario y del inmueble para validaciones adicionales
        self.usuario = kwargs.pop('usuario', None)
        self.inmueble = kwargs.pop('inmueble', None)
        super(CalificacionForm, self).__init__(*args, **kwargs)

    def clean(self):
        # Limpia y valida los datos
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        aun_renta = cleaned_data.get('aun_renta')

        # Validación de fechas
        if fecha_inicio and fecha_fin:
            if fecha_fin < fecha_inicio:
                raise ValidationError('La fecha de fin no puede ser anterior a la fecha de inicio.')

        # Validar que el usuario tiene una reserva activa con el inmueble
        # Asegúrate de que self.usuario e inmueble estén definidos
        if self.usuario and self.inmueble:
            if not Reserva.objects.filter(usuario=self.usuario, inmueble=self.inmueble, estado_pago=True).exists():
                raise ValidationError('Debes reservar este inmueble y completar el pago antes de calificarlo.')

        return cleaned_data

class ReservaForm(forms.Form):
    nombre = forms.CharField(label='Nombre', max_length=100, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    apellido = forms.CharField(label='Apellido', max_length=100, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    nombre_usuario = forms.CharField(label='Nombre de Usuario', max_length=100, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    fecha_entrada = forms.DateField(label='Fecha de Entrada', widget=forms.SelectDateWidget())
    fecha_salida = forms.DateField(label='Fecha de Salida', widget=forms.SelectDateWidget())
    numero_personas = forms.IntegerField(label='Número de Personas', min_value=1)
    comentarios = forms.CharField(label='Comentarios', widget=forms.Textarea, required=False)


