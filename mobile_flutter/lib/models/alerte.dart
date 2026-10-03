/// Représente une alerte de fraude (AlerteFraude) telle que renvoyée par l'API.
class Alerte {
  final int id;
  final int pointageId;
  final String typeFraude;   // 'hors_zone' | 'doublon' | 'coords_fixes' | 'heure_invalide' | 'spoofing_gps'
  final double? scoreIa;
  final String? niveauSeverite; // 'FAIBLE' | 'MOYEN' | 'ELEVE' | 'CRITIQUE'
  final String statut;          // 'NON_TRAITEE' | 'EN_INVESTIGATION' | 'FRAUDE_CONFIRMEE' | 'FAUSSE_ALERTE'
  final String? commentaire;
  final Map<String, dynamic>? analyseIa; // facteurs détaillés, si calculés par le modèle IA
  final DateTime timestamp;
  final String etudiantNom;
  final String etudiantMatricule;
  final String moduleCode;
  final String dateSession;

  Alerte({
    required this.id,
    required this.pointageId,
    required this.typeFraude,
    this.scoreIa,
    this.niveauSeverite,
    required this.statut,
    this.commentaire,
    this.analyseIa,
    required this.timestamp,
    required this.etudiantNom,
    required this.etudiantMatricule,
    required this.moduleCode,
    required this.dateSession,
  });

  bool get estTraitee => statut == 'FRAUDE_CONFIRMEE' || statut == 'FAUSSE_ALERTE';
  bool get estConfirmee => statut == 'FRAUDE_CONFIRMEE';

  factory Alerte.fromJson(Map<String, dynamic> json) {
    return Alerte(
      id: json['id'] is int ? json['id'] as int : int.tryParse('${json['id']}') ?? 0,
      pointageId: json['pointage'] is int ? json['pointage'] as int : int.tryParse('${json['pointage']}') ?? 0,
      typeFraude: json['type_fraude']?.toString() ?? '',
      scoreIa: (json['score_ia'] as num?)?.toDouble(),
      niveauSeverite: json['niveau_severite']?.toString(),
      statut: json['statut']?.toString() ?? 'NON_TRAITEE',
      commentaire: json['commentaire']?.toString(),
      analyseIa: json['analyse_ia'] is Map<String, dynamic> ? json['analyse_ia'] as Map<String, dynamic> : null,
      timestamp: DateTime.tryParse(json['timestamp']?.toString() ?? '') ?? DateTime.now(),
      etudiantNom: json['etudiant_nom']?.toString() ?? '',
      etudiantMatricule: json['etudiant_matricule']?.toString() ?? '',
      moduleCode: json['module_code']?.toString() ?? '',
      dateSession: json['date_session']?.toString() ?? '',
    );
  }
}