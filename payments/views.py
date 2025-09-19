import stripe
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(["POST"])
def create_checkout_session(request):
    try:
        amount = request.data.get("amount")      # monto en USD
        currency = request.data.get("currency", "usd")
        name = request.data.get("name", "Cliente")
        email = request.data.get("email", None)

        if not amount:
            return Response({"error": "Amount requerido"}, status=status.HTTP_400_BAD_REQUEST)

        # Stripe requiere "unit_amount" en centavos
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": currency,
                        "product_data": {"name": f"Reserva Área - {name}"},
                        "unit_amount": int(amount) * 100,  # USD → centavos
                    },
                    "quantity": 1,
                },
            ],
            mode="payment",
            customer_email=email,
            success_url="http://localhost:5173/reservas?success=true",
            cancel_url="http://localhost:5173/reservas?canceled=true",
        )

        return Response({"sessionId": session.id})

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
