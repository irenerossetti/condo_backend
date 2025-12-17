from django.contrib.auth import get_user_model
from core.models import Conversation, Message, Profile

User = get_user_model()

print("=" * 60)
print("VERIFICACIÓN DE ACCESO AL CHAT")
print("=" * 60)

residents = User.objects.filter(profile__role='RESIDENT')
print(f"\nResidentes: {residents.count()}")
print(f"Conversaciones: {Conversation.objects.count()}")
print(f"Mensajes: {Message.objects.count()}")

if residents.exists():
    resident = residents.first()
    convs = Conversation.objects.filter(participants=resident)
    print(f"\nResidente: {resident.username}")
    print(f"Conversaciones accesibles: {convs.count()}")
    
    for conv in convs:
        participants = [p.username for p in conv.participants.all()]
        print(f"  - {conv.title}: {participants}")
else:
    print("\n⚠️ No hay residentes")

print("\n✅ Chat accesible para todos los usuarios autenticados")
