# listings/views.py
from decouple import config
from django.contrib.auth import login
from django.contrib import messages
from django.conf import settings

from django.http import HttpResponse
from django.conf import settings
from django.views.generic import CreateView
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404 
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import update_session_auth_hash,logout
from .forms import CustomUserCreationForm, EmailAuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .forms import InmuebleForm, CalificacionForm,CustomUserUpdateForm, CustomPasswordChangeForm
from .models import ImagenInmueble, Inmueble,Calificacion, Reserva
from django.http import Http404
from django.urls import reverse_lazy
import stripe
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import AnonymousUser

stripe.api_key = config('STRIPE_SECRET_KEY')
endpoint_secret = config('STRIPE_WEBHOOK_SECRET')



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
    success_url = reverse_lazy('login')  # Redirigir al login después del registro exitoso

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Cuenta creada exitosamente. Por favor, inicia sesión.")
        return response
    def form_invalid(self, form):
        messages.error(self.request, "El formulario no se llenó correctamente, verifica y vuelve a intentar.")
        return super().form_invalid(form)

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

@login_required      
def logout_and_redirect_mis_inmuebles(request):
    logout(request)  # Cerrar sesión del usuario
    return redirect('mis_inmuebles')  # Redirigir a la página de "Mis inmuebles"

@login_required
def detalle_inmueble(request, inmueble_id):
    inmueble = get_object_or_404(Inmueble, id=inmueble_id)
    comentarios = inmueble.comentarios.all()
  

    if request.method == 'POST':
        comentario_form = CalificacionForm(request.POST)
        if comentario_form.is_valid():
            comentario = comentario_form.save(commit=False)
            comentario.usuario = request.user
            comentario.inmueble = inmueble
            comentario.save()
            return redirect('detalle_inmueble', inmueble_id=inmueble.id)
    else:
        comentario_form = CalificacionForm()

    return render(request, 'detalle_inmueble.html', {
        'inmueble': inmueble,
        'comentarios': comentarios,
        'comentario_form': comentario_form
    })

def ver_comentarios(request, inmueble_id):
    # Obtiene el inmueble por ID
    inmueble = get_object_or_404(Inmueble, id=inmueble_id)
    calificaciones = Calificacion.objects.filter(inmueble=inmueble)

    # Marca los comentarios del arrendatario como "verificados"
    for comentario in calificaciones:
        comentario.verificado = comentario.usuario == inmueble.arrendatario

    return render(request, 'ver_comentarios.html', {
        'inmueble': inmueble,
        'comentarios': calificaciones,
        'arrendatario': inmueble.arrendatario
    })
@login_required
def perfil(request):
    return render(request, 'perfil.html', {'user': request.user})

@login_required
def inmuebles_rentados(request):
    usuario = request.user
    
    reservas_rentadas = Reserva.objects.filter(usuario=usuario, estado_pago=True)
    return render(request, 'inmuebles_rentados.html', {'reservas_rentadas': reservas_rentadas})
    # Filtrar los inmuebles que el usuario ha rentado con el pago completado
@login_required
def volver_a_rentar(request, inmueble_id):
    inmueble = get_object_or_404(Inmueble, id=inmueble_id, usuario=request.user)

    # Verifica si el inmueble está actualmente rentado
    if inmueble.estado == 'rentado':
        # Cambiar el estado a disponible
        inmueble.estado = 'disponible'
        inmueble.save()

        # Eliminar la reserva asociada si existe
        reserva = Reserva.objects.filter(inmueble=inmueble, estado_pago=True).first()
        if reserva:
            reserva.delete()
            messages.success(request, 'El inmueble ha vuelto a estar disponible y la reserva ha sido eliminada.')

    else:
        messages.error(request, 'El inmueble no se encuentra en estado de renta.')

    return redirect('mis_inmuebles')

@login_required
def editar_perfil(request):
    
    if request.method == 'POST':
        if 'btn_guardar_perfil' in request.POST:
            user_form = CustomUserUpdateForm(request.POST, instance=request.user)
            if user_form.is_valid():
                user_form.save()
                messages.success(request, "Perfil actualizado exitosamente.")
                return redirect('editar_perfil')
            else:
                messages.error(request, "Hubo un error al actualizar tu perfil. Revisa la información e inténtalo de nuevo.")
        
        elif 'btn_cambiar_contrasena' in request.POST:
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Evita desconectar al usuario
                messages.success(request, "Contraseña actualizada exitosamente.")
                return redirect('editar_perfil')
            else:
                messages.error(request, "Hubo un error al actualizar la contraseña. Verifica la información e inténtalo de nuevo.")
    else:
        user_form = CustomUserUpdateForm(instance=request.user)
        password_form = PasswordChangeForm(user=request.user)
    

    return render(request, 'editar_perfil.html', {
        'form': user_form,
        'password_form': password_form
    })
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
def publicar_inmueble(request):
    if request.method == 'POST':
        inmueble_form = InmuebleForm(request.POST, request.FILES)

        if inmueble_form.is_valid():
            # Valida el número de imágenes antes de guardar el inmueble
            imagenes = request.FILES.getlist('imagenes')
            if len(imagenes) < 7 or len(imagenes) > 15:
                messages.error(request, "Debes subir entre 7 y 15 imágenes.")
                return render(request, 'publicar_inmueble.html', {'inmueble_form': inmueble_form})

            # Guarda el inmueble
            inmueble = inmueble_form.save(commit=False)
            inmueble.usuario = request.user  # Asegúrate de asignar al usuario autenticado
            
            try:
                inmueble.save()
                print("Inmueble guardado correctamente:", inmueble)

                # Procesa las imágenes subidas
                for imagen in imagenes:
                    try:
                        ImagenInmueble.objects.create(inmueble=inmueble, imagen=imagen)
                    except Exception as e:
                        print("Error al guardar la imagen:", str(e))
                        messages.error(request, "Hubo un error al guardar la imagen. Inténtalo de nuevo.")
                        return render(request, 'publicar_inmueble.html', {'inmueble_form': inmueble_form})

                messages.success(request, "Inmueble publicado exitosamente.")
                return redirect('home')
            except Exception as e:
                print("Error al guardar el inmueble:", str(e))
                messages.error(request, "Hubo un error al publicar el inmueble. Inténtalo de nuevo.")
        else:
            # Imprime los errores del formulario si no es válido
            print("Errores del formulario:", inmueble_form.errors)
            messages.error(request, "Hubo un error en el formulario. Revisa la información e inténtalo de nuevo.")

    else:
        inmueble_form = InmuebleForm()

    return render(request, 'publicar_inmueble.html', {'inmueble_form': inmueble_form})

@login_required
def inmueble_detalle(request, inmueble_id):
    # Obtén el inmueble
    inmueble = get_object_or_404(Inmueble, id=inmueble_id)
    

    # Obtén las calificaciones asociadas al inmueble
    comentarios = Calificacion.objects.filter(inmueble=inmueble)
    
    # Inicializa el formulario de calificación
    comentario_form = CalificacionForm()
    
    
    # Verificar si el usuario tiene una reserva activa y pagada para este inmueble
    reserva_activa = Reserva.objects.filter(
        usuario=request.user,
        inmueble=inmueble,
        estado_pago=True
    ).exists()

    # Contexto para pasar a la plantilla
    context = {
        'inmueble': inmueble,
        'imagenes': inmueble.imagenes.all(),
        'comentarios': comentarios,
        'comentario_form': comentario_form,
        'reserva_activa': reserva_activa,
    }
    return render(request, 'inmueble_detalle.html', context)


@login_required
def calificar_inmueble(request, inmueble_id):
    inmueble = get_object_or_404(Inmueble, id=inmueble_id)

    # Verificar si el usuario tiene una reserva activa y pagada para este inmueble
    try:
        reserva_activa = Reserva.objects.get(
            usuario=request.user,
            inmueble=inmueble,
            estado_pago=True  # Verificar que el pago esté completado
        )
    except Reserva.DoesNotExist:
        reserva_activa = None

    # Si no hay una reserva activa y pagada, redirigir al detalle del inmueble con un mensaje de error
    if not reserva_activa:
        messages.error(request, "Debes reservar este inmueble y completar el pago antes de poder calificarlo.")
        return redirect('inmueble_detalle', inmueble_id=inmueble.id)

    # Inicializar el formulario con los valores de usuario e inmueble
    if request.method == 'POST':
        form = CalificacionForm(request.POST, usuario=request.user, inmueble=inmueble)
        if form.is_valid():
            # Guardar la calificación
            calificacion = form.save(commit=False)
            calificacion.inmueble = inmueble
            calificacion.usuario = request.user  # Asignar el usuario autenticado
            calificacion.verificado = True  # Marcar la calificación como verificada
            calificacion.save()
            # Redirigir al detalle del inmueble después de calificar
            return redirect('inmueble_detalle', inmueble_id=inmueble.id)
        else:
            # Imprimir los errores si el formulario no es válido
            print(form.errors)
    else:
        form = CalificacionForm(usuario=request.user, inmueble=inmueble)

    return render(request, 'calificar_inmueble.html', {
        'form': form,
        'inmueble': inmueble,
        'reserva_activa': True  # Sabemos que la reserva está activa si llega hasta aquí
    })

@login_required
def crear_sesion_pago(request):
    stripe.api_key = config('STRIPE_SECRET_KEY')
    
    if request.method == 'POST':
        inmueble_id = request.POST.get('inmueble_id')

        # Validar que inmueble_id sea válido antes de intentar obtener el inmueble
        try:
            inmueble = Inmueble.objects.get(id=inmueble_id)
            if Reserva.objects.filter(inmueble=inmueble, estado_pago=True).exists():
                return render(request, 'inmueble_ya_rentado.html', {
            'mensaje': 'Este inmueble ya ha sido rentado.'
        })

                

           
        except Inmueble.DoesNotExist:
            return JsonResponse({'error': 'Inmueble no encontrado.'}, status=400)

        usuario = request.user  # Obtener el usuario actual

        # Verificar si el inmueble ya está reservado por alguien más
        if Reserva.objects.filter(inmueble=inmueble, estado_pago=False).exists():
            # Si existe una reserva activa, no permitimos crear una nueva
            return JsonResponse({'error': 'Este inmueble ya está reservado por otro usuario.'}, status=400)

        # Crear la reserva con estado_pago = False antes del pago
        try:
            nueva_reserva = Reserva(usuario=usuario, inmueble=inmueble)
            nueva_reserva.save()
            print(f"Reserva creada con éxito: {nueva_reserva}")
        except Exception as e:
            print(f"Error al crear la reserva: {str(e)}")
            return JsonResponse({'error': 'No se pudo crear la reserva.'}, status=400)
        
        precio_cobrar = int(inmueble.precio * 100) 

        # Crear la sesión de pago con Stripe
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'mxn',
                        'product_data': {
                            'name': f'Reserva del Inmueble: {inmueble}',  # Información del inmueble
                        },
                        'unit_amount': precio_cobrar,  # Precio en centavos (20.00 MXN)
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url = 'https://inmueblesesime-6.onrender.com/pago-exitoso/',
                cancel_url = 'https://inmueblesesime-6.onrender.com//pago-cancelado/',
               
                metadata={
                    'usuario_id': usuario.id,
                    'inmueble_id': inmueble.id,
                }
            )
            return redirect(session.url, code=303)
        except stripe.error.StripeError as e:
            # Manejo de errores específicos de Stripe
            print(f"Error al crear la sesión de pago: {str(e)}")
            return JsonResponse({'error': 'No se pudo crear la sesión de pago.'}, status=400)
        except Exception as e:
            # Cualquier otro error inesperado
            print(f"Error inesperado: {str(e)}")
            return JsonResponse({'error': 'Ha ocurrido un error inesperado.'}, status=400)



def pago_exitoso(request):
    return render(request, 'pago_exitoso.html')

def pago_cancelado(request):
    return render(request, 'pago_cancelado.html')



endpoint_secret = config('STRIPE_WEBHOOK_SECRET')

@csrf_exempt
def stripe_webhook(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        # Construir el evento verificando la firma con el endpoint_secret
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret, tolerance=600  # 10 minutos de tolerancia
        )
    except ValueError as e:
        print("Invalid payload")
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        print("Invalid signature")
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return JsonResponse({'error': 'Unexpected error'}, status=400)

    # Imprimir el tipo de evento recibido para confirmar que llegó correctamente
    print(f"Evento recibido: {event['type']}")

    # Manejar el evento específico `checkout.session.completed`
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # Obtener los detalles relevantes de la sesión
        usuario_id = session.get('metadata', {}).get('usuario_id')
        inmueble_id = session.get('metadata', {}).get('inmueble_id')

        # Imprimir información de depuración
        print(f"Metadata recibida - Usuario ID: {usuario_id}, Inmueble ID: {inmueble_id}")

        if usuario_id and inmueble_id:
            try:
                usuario = User.objects.get(id=usuario_id)
                inmueble = Inmueble.objects.get(id=inmueble_id)

                # Actualizar la reserva que tiene estado_pago=False a True
                reserva = Reserva.objects.filter(usuario=usuario, inmueble=inmueble, estado_pago=False).first()

                if reserva:
                    reserva.estado_pago = True
                    reserva.save()
                    inmueble.estado = 'rentado'
                    inmueble.save()
                    print(f"Reserva actualizada con éxito: {reserva}")
                else:
                    print(f"No se encontró una reserva para actualizar - Usuario ID: {usuario_id}, Inmueble ID: {inmueble_id}")

            except User.DoesNotExist:
                print(f"Usuario con ID {usuario_id} no existe")
            except Inmueble.DoesNotExist:
                print(f"Inmueble con ID {inmueble_id} no existe")
            except Exception as e:
                print(f"Error inesperado al actualizar la reserva: {str(e)}")

    return JsonResponse({'status': 'success'}, status=200)