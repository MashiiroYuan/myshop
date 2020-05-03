from django.shortcuts import render, redirect, get_object_or_404
import braintree
from orders.models import Order
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
import weasyprint
from django.conf import settings
from io import BytesIO
from shop.recommender import Recommender

# Create your views here.
def payment_process(request):
    order_id = request.session.get('order_id')
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        # 获得token
        nonce = request.POST.get('payment_method_nonce', None)
        # 使用token 创建提交交易
        result = braintree.Transaction.sale({
            'amount': '{:2f}'.format(order.get_total_cost()),
            'payment_method_nonce': nonce,
            'options': {'submit_for_settlement': True, }

        })
        if result.is_success:
            # 更改支付状态
            order.paid = True
            # 保存id
            order.braintree_id = result.transaction.id
            order.save()
            #更新redis本次购买商品
            r=Recommender()
            order_items=[order_item.product for order_item in order.items.all()]
            r.products_bought(order_items)
            # 创建代有pdf的发票
            subject = 'My shop - Invoice no {}'.format(order_id)
            message = 'Please,find attached the invouce for your recent purchase'
            email = EmailMessage(subject, message, 'admin@myshop.com', [order.email])

            # 生成pdf
            html = render_to_string('orders/order/pdf.html', {'order': order})
            out = BytesIO()
            stylesheets = [weasyprint.CSS(settings.STATIC_ROOT + 'css/pdf.css')]
            weasyprint.HTML(string=html).write_pdf(out, stylesheets=stylesheets)

            # 附加pdf附件
            email.attach('order_{}.pdf'.format(order_id), out.getvalue(), 'application/pdf')
            # 发送邮件
            email.send()
            return redirect('payment:done')
        else:
            return redirect('payment:canceled')
    else:
        # 生成临时token交给js
        client_token = braintree.ClientToken.generate()
        return render(request, 'payment/process.html', {'order': order, 'client_token': client_token})


def payment_done(request):
    return render(request, 'payment/done.html')


def payment_canceled(request):
    return render(request, 'payment/canceled.html')
