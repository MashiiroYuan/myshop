from celery import task
from django.core.mail import send_mail
from .models import Order


@task
def order_created(order_id):
    order = Order.objects.get(id=order_id)

    subject = 'Order {}'.format(order.id)
    message = "Dear {}, \n\n You success placed order Order id is {}".format(order.first_name, order.id)
    mail_sent = send_mail()
