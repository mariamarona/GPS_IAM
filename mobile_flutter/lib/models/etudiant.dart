/// Représente un étudiant tel que renvoyé par l'API IAMGPS.
///
/// Les champs de statistiques (presences, totalSessions, tauxPresence,
/// statutSeuil) sont optionnels : ils ne sont renseignés que quand l'étudiant
/// est affiché dans le contexte d'un module précis (ex: le tableau "Étudiants
/// inscrits" de l'écran enseignant). Ailleurs, ils restent simplement null.
class Etudiant {
  final String id;
  final String matricule;
  final String nom;
  final String prenom;
  final String? email;

  final int? presences;
  final int? totalSessions;
  final double? tauxPresence;
  final String? statutSeuil; // 'OK' | 'SOUS_SEUIL'

  Etudiant({
    required this.id,
    required this.matricule,
    required this.nom,
    required this.prenom,
    this.email,
    this.presences,
    this.totalSessions,
    this.tauxPresence,
    this.statutSeuil,
  });

  String get nomComplet => '$prenom $nom';

  bool get estSousSeuil => statutSeuil == 'SOUS_SEUIL';

  factory Etudiant.fromJson(Map<String, dynamic> json) {
    return Etudiant(
      id: json['id']?.toString() ?? '',
      matricule: json['matricule']?.toString() ?? '',
      nom: json['nom']?.toString() ?? '',
      prenom: json['prenom']?.toString() ?? '',
      email: json['email']?.toString(),
      presences: json['presences'] is int ? json['presences'] as int : null,
      totalSessions: json['total_sessions'] is int ? json['total_sessions'] as int : null,
      tauxPresence: (json['taux_presence'] as num?)?.toDouble(),
      statutSeuil: json['statut']?.toString(),
    );
  }
}