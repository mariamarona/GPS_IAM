/// Représente un pointage (une "présence") tel que renvoyé par l'API IAMGPS —
/// que ce soit dans l'historique de l'étudiant ou le résultat d'un pointage
/// qui vient d'être validé.
class Presence {
  final String id;
  final String date;      // format YYYY-MM-DD renvoyé par le backend
  final String cours;     // code du module (ex: 'SYC-BI')
  final String? lieu;
  final DateTime timestamp;
  final String statut;    // 'VALIDE' | 'HORS_ZONE' | 'REJETE'
  final double? distanceM;

  Presence({
    required this.id,
    required this.date,
    required this.cours,
    this.lieu,
    required this.timestamp,
    required this.statut,
    this.distanceM,
  });

  bool get estValide => statut == 'VALIDE';
  bool get estHorsZone => statut == 'HORS_ZONE';

  /// Date au format français (JJ/MM/AAAA) à partir du 'YYYY-MM-DD' renvoyé par
  /// le backend. Si le format est inattendu, renvoie la valeur brute telle quelle.
  String get dateFormatee {
    final parties = date.split('-');
    if (parties.length != 3) return date;
    return '${parties[2]}/${parties[1]}/${parties[0]}';
  }

  /// Libellé lisible du statut, pour l'affichage (au lieu du code technique).
  String get libelleStatut {
    switch (statut) {
      case 'VALIDE':
        return 'Présent';
      case 'HORS_ZONE':
        return 'Hors zone';
      case 'REJETE':
        return 'Rejeté';
      default:
        return statut;
    }
  }

  /// Heure locale formatée (HH:MM:SS), en tenant compte du fuseau de l'appareil —
  /// c'est le timestamp ISO complet renvoyé par le backend qui garantit que
  /// cette heure correspond exactement à l'heure de l'utilisateur, quel que
  /// soit le fuseau configuré côté serveur.
  String get heureFormatee {
    final h = timestamp.toLocal();
    String deuxChiffres(int n) => n.toString().padLeft(2, '0');
    return '${deuxChiffres(h.hour)}:${deuxChiffres(h.minute)}:${deuxChiffres(h.second)}';
  }

  factory Presence.fromJson(Map<String, dynamic> json) {
    return Presence(
      id: json['id']?.toString() ?? '',
      date: json['date']?.toString() ?? '',
      cours: json['cours']?.toString() ?? '',
      lieu: json['lieu']?.toString(),
      timestamp: DateTime.tryParse(json['timestamp']?.toString() ?? '') ?? DateTime.now(),
      statut: json['statut']?.toString() ?? '',
      distanceM: (json['distance_m'] as num?)?.toDouble(),
    );
  }
}