from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
import bcrypt

from .models import Utilisateur


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email    = request.data.get('email')
    password = request.data.get('mot_de_passe')

    if not email or not password:
        return Response({'error': 'Email et mot de passe requis'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        utilisateur = Utilisateur.objects.get(email=email)
    except Utilisateur.DoesNotExist:
        return Response({'error': 'Email ou mot de passe incorrect'}, status=status.HTTP_401_UNAUTHORIZED)

    if not bcrypt.checkpw(password.encode('utf-8'), utilisateur.mot_de_passe.encode('utf-8')):
        return Response({'error': 'Email ou mot de passe incorrect'}, status=status.HTTP_401_UNAUTHORIZED)

    if not utilisateur.is_active:
        return Response({'error': 'Compte désactivé'}, status=status.HTTP_403_FORBIDDEN)

    utilisateur.last_login = timezone.now()
    utilisateur.save()

    refresh = RefreshToken()
    refresh['user_id']   = str(utilisateur.id)
    refresh['role']      = utilisateur.role
    refresh['matricule'] = utilisateur.matricule

    return Response({
        'access':  str(refresh.access_token),
        'refresh': str(refresh),
        'utilisateur': {
            'id':        str(utilisateur.id),
            'matricule': utilisateur.matricule,
            'nom':       utilisateur.nom,
            'prenom':    utilisateur.prenom,
            'email':     utilisateur.email,
            'role':      utilisateur.role,
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def logout(request):
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return Response({'error': 'Refresh token requis'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Déconnexion réussie'}, status=status.HTTP_200_OK)
    except Exception:
        return Response({'error': 'Token invalide'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    token = request.data.get('refresh')
    if not token:
        return Response({'error': 'Refresh token requis'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        refresh    = RefreshToken(token)
        new_access = str(refresh.access_token)
        return Response({'access': new_access}, status=status.HTTP_200_OK)
    except Exception:
        return Response({'error': 'Token invalide ou expiré'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([AllowAny])
def change_password(request):
    utilisateur_id = request.data.get('utilisateur_id')
    ancien_mdp     = request.data.get('ancien_mot_de_passe')
    nouveau_mdp    = request.data.get('nouveau_mot_de_passe')

    if not all([utilisateur_id, ancien_mdp, nouveau_mdp]):
        return Response(
            {'error': 'utilisateur_id, ancien_mot_de_passe et nouveau_mot_de_passe sont requis'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(nouveau_mdp) < 6:
        return Response(
            {'error': 'Le nouveau mot de passe doit contenir au moins 6 caractères'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        utilisateur = Utilisateur.objects.get(id=utilisateur_id)
    except Utilisateur.DoesNotExist:
        return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)

    if not bcrypt.checkpw(ancien_mdp.encode('utf-8'), utilisateur.mot_de_passe.encode('utf-8')):
        return Response({'error': 'Ancien mot de passe incorrect'}, status=status.HTTP_401_UNAUTHORIZED)

    nouveau_hashed = bcrypt.hashpw(nouveau_mdp.encode('utf-8'), bcrypt.gensalt())
    utilisateur.mot_de_passe = nouveau_hashed.decode('utf-8')
    utilisateur.save()

    return Response({'message': 'Mot de passe modifié avec succès'}, status=status.HTTP_200_OK)