# core/utils.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

def send_verification_email(user, password):
    domain = getattr(settings, 'SITE_DOMAIN', '127.0.0.1:8000')
    protocol = 'https' if not settings.DEBUG else 'http'
    activation_link = f"{protocol}://{domain}/verify-email/{user.username}/"

    context = {
        'user': user,
        'temp_password': password,
        'link': activation_link
    }

    # ВНИМАНИЕ: Проверь этот путь! 
    # Он должен точно совпадать с папками в templates
    try:
        html_content = render_to_string('core/verify_email.html', context)
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(
            "Подтверждение регистрации Vkusnevich",
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        print(f"Письмо успешно отправлено на {user.email}")
        
    except Exception as e:
        # Это выведет ошибку в консоль, если что-то пойдет не так
        print(f"Ошибка внутри send_verification_email: {e}")
        raise e # Оставляем raise, чтобы view тоже видела ошибку

