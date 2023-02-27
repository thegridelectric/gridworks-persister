import random


secret_django_key = "".join(
    [
        random.SystemRandom().choice(
            "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
        )
        for i in range(50)
    ]
)
print(secret_django_key)
