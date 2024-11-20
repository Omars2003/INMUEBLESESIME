# listings/views.py
from django.contrib.auth import login
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.conf import settings
from django.views.generic import CreateView
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404 
from django.contrib.auth.forms import AuthenticationForm
from .forms import CustomUserCreationForm, EmailAuthenticationForm
from django.contrib.auth.decorators import login_required
from .forms import InmuebleForm, CalificacionForm, AsignarArrendatarioForm, ReservaForm
from .models import ImagenInmueble, Inmueble, HistorialRenta
from django.http import Http404

def home(request):
    # Obtén los valores de los filtros desde los parámetros GET de la URL
    tipo = request.GET.get('tipo')
    costo = request.GET.get('costo')
    distancia = request.GET.get('distancia')

    # Empieza con todos los inmuebles
    inmuebles = Inmueble.objects.all()

    # Filtra según el tipo de inmueble si está presente en la URL
    if tipo:
        inmuebles = inmuebles.filter(tipo_inmueble=tipo)

    # Filtra por rango de precio si el filtro de costo está presente
    if costo:
        min_price, max_price = map(int, costo.split('-'))
        inmuebles = inmuebles.filter(precio__gte=min_price, precio__lte=max_price)

    # Filtra por distancia si está presente
    if distancia:
        inmuebles = inmuebles.filter(distancia=distancia)

    return render(request, 'home.html', {'inmuebles': inmuebles})
class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'register.html'
    success_url = settings.LOGIN_REDIRECT_URL

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Cuenta creada exitosamente. Por favor, inicia sesión.")
        return response

class CustomLoginView(View):
    form_class = EmailAuthenticationForm
    template_name = 'login.html'

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(data=request.POST)
        if form.is_valid():
            user = form.cleaned_data.get("user")
            login(request, user)
            messages.success(request, "Has iniciado sesión exitosamente.")
            return redirect(settings.LOGIN_REDIRECT_URL)
        else:
            messages.error(request, "Lo sentimos, el correo y/o contraseña no coinciden, intenta de nuevo.")
            return render(request, self.template_name, {'form': form})
        
def inmueble_detalle(request, inmueble_id):
    inmueble = get_object_or_404(Inmueble, id=inmueble_id)  # Obtiene el inmueble
    return render(request, 'detalle_inmueble.html', {'inmueble': inmueble}) 

@login_required
def perfil(request):
    return render(request, 'perfil.html', {'user': request.user})


@login_required
def editar_perfil(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil actualizado exitosamente.")
            return redirect('perfil')
    else:
        form = CustomUserCreationForm(instance=request.user)
    
    return render(request, 'editar_perfil.html', {'form': form})

@login_required
def mis_inmuebles(request):
    inmuebles = Inmueble.objects.filter(usuario=request.user)  # Filtra por usuario actual
    return render(request, 'mis_inmuebles.html', {'inmuebles': inmuebles})

@login_required
def editar_inmueble(request, inmueble_id):
    inmueble = get_object_or_404(Inmueble, id=inmueble_id)

    # Verifica si el usuario es el propietario del inmueble
    if request.user != inmueble.usuario:
        return redirect('mis_inmuebles')

    if request.method == 'POST':
        # Formulario para editar los datos del inmueble
        inmueble_form = InmuebleForm(request.POST, instance=inmueble, files=request.FILES)

        if inmueble_form.is_valid():
            # Guardar los cambios del inmueble
            inmueble_form.save()

            # Si hay imágenes en el formulario, las guardamos
            imagenes = request.FILES.getlist('imagenes')
            for imagen in imagenes:
                ImagenInmueble.objects.create(inmueble=inmueble, imagen=imagen)

            # Redirigir después de guardar
            return redirect('mis_inmuebles')

    else:
        # Si es una solicitud GET, mostrar el formulario con los datos actuales
        inmueble_form = InmuebleForm(instance=inmueble)

    return render(request, 'editar_inmueble.html', {
        'inmueble_form': inmueble_form,
        'inmueble': inmueble
    })
@login_required
def eliminar_imagen(request, imagen_id):
    imagen = get_object_or_404(ImagenInmueble, id=imagen_id)

    # Verifica si el usuario actual tiene permisos para eliminar esta imagen
    if request.user == imagen.inmueble.usuario:
        imagen.delete()
    
    # Redirige al formulario de edición del inmueble
    return redirect('editar_inmueble', inmueble_id=imagen.inmueble.id)

@login_required
def eliminar_inmueble(request, inmueble_id):
    inmueble = get_object_or_404(Inmueble, id=inmueble_id, usuario=request.user)
    if request.method == 'POST':
        inmueble.delete()
        return redirect('mis_inmuebles')
    return render(request, 'eliminar_inmueble.html', {'inmueble': inmueble})
@login_required
def asignar_arrendatario(request, inmueble_id):
    inmueble = get_object_or_404(Inmueble, id=inmueble_id, arrendador=request.user)
    
    if request.method == "POST":
        form = AsignarArrendatarioForm(request.POST, instance=inmueble)
        if form.is_valid():
            form.save()
            return redirect('inmueble_detalle', inmueble_id=inmueble.id)
    else:
        form = AsignarArrendatarioForm(instance=inmueble)

    return render(request, 'asignar_arrendatario.html', {'form': form, 'inmueble': inmueble})

@login_required
def reservar_inmueble_formulario(request, inmueble_id):
    inmueble = get_object_or_404(Inmueble, id=inmueble_id)

    if request.method == 'POST':
        form = ReservaForm(request.POST)
        if form.is_valid():
            # Aquí puedes guardar los datos del formulario si fuera necesario.
            # Vamos a redirigir a la página de detalles después de la reserva
            return redirect('detalle_inmueble', inmueble_id=inmueble.id)
    else:
        # Prellenar el formulario con el nombre y apellido del usuario actual
        form = ReservaForm(initial={
            'nombre': request.user.first_name,
            'apellido': request.user.last_name,
            'nombre_usuario': request.user.username
        })

    return render(request, 'reservar_inmueble.html', {'form': form, 'inmueble': inmueble})

@login_required
def reservar_inmueble(request, inmueble_id):
    inmueble = get_object_or_404(Inmueble, id=inmueble_id)

    # Asegúrate de que el inmueble no esté ya reservado
    if inmueble.arrendatario is None:
        inmueble.arrendatario = request.user
        inmueble.save()

    return redirect('detalle_inmueble', inmueble_id=inmueble.id) 
@login_required
def publicar_inmueble(request):
    if request.method == 'POST':
        inmueble_form = InmuebleForm(request.POST)

        if inmueble_form.is_valid():
            # Guarda el inmueble
            inmueble = inmueble_form.save(commit=False)
            inmueble.arrendador = request.user  # Asigna automáticamente el usuario autenticado como arrendador
            inmueble.save()

            # Procesa las imágenes subidas
            imagenes = request.FILES.getlist('imagenes')
            if len(imagenes) < 7 or len(imagenes) > 15:
                return render(request, 'publicar_inmueble.html', {
                    'inmueble_form': inmueble_form,
                    'error': "Debes subir entre 7 y 15 imágenes."
                })

            for imagen in imagenes:
                ImagenInmueble.objects.create(inmueble=inmueble, imagen=imagen)

            return redirect('home')  # Redirige a la página principal

    else:
        inmueble_form = InmuebleForm()

    return render(request, 'publicar_inmueble.html', {'inmueble_form': inmueble_form})

@login_required
def calificar_inmueble(request, inmueble_id):
    inmueble = get_object_or_404(Inmueble, id=inmueble_id)

    # Verifica si el usuario es el arrendatario
    if inmueble.arrendatario != request.user:
        return HttpResponseForbidden("No puedes calificar este inmueble porque no eres el arrendatario.")

    # Procesa la calificación (como guardar en base de datos)
    if request.method == "POST":
        form = CalificacionForm(request.POST)
        if form.is_valid():
            calificacion = form.save(commit=False)
            calificacion.inmueble = inmueble
            calificacion.usuario = request.user
            calificacion.save()
            return redirect('inmueble_detalle', inmueble_id=inmueble.id)
    else:
        form = CalificacionForm()

    return render(request, 'calificar_inmueble.html', {'form': form, 'inmueble': inmueble})



def inmueble_detalle(request, inmueble_id):
    inmueble = get_object_or_404(Inmueble, id=inmueble_id)
    imagenes = inmueble.imagenes.all()  # Suponiendo que tienes un campo relacionado llamado `imagenes` en tu modelo
    return render(request, 'inmueble_detalle.html', {'inmueble': inmueble, 'imagenes': imagenes})

def calificar_inmueble(request, inmueble_id):
    inmueble = get_object_or_404(Inmueble, id=inmueble_id)

    # Verificar si el usuario ha rentado este inmueble
    if not HistorialRenta.objects.filter(usuario=request.user, inmueble=inmueble).exists():
        messages.error(request, "No puedes calificar este inmueble porque no lo has rentado.")
        return redirect('inmueble_detalle', inmueble_id=inmueble.id)

    # Procesar el formulario de calificación
    if request.method == "POST":
        form = CalificacionForm(request.POST)
        if form.is_valid():
            calificacion = form.save(commit=False)
            calificacion.usuario = request.user
            calificacion.inmueble = inmueble
            calificacion.save()
            messages.success(request, "Gracias por calificar el inmueble.")
            return redirect('inmueble_detalle', inmueble_id=inmueble.id)
    else:
        form = CalificacionForm()

    return render(request, 'calificar_inmueble.html', {'form': form, 'inmueble': inmueble})