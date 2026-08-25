from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group

from accounts.models import User
from equipment.models import (
    EquipmentVOR, EquipmentILS, EquipmentDME, EquipmentRadar, EquipmentVCS,
    MeasurementLog, STATUS_OK, STATUS_DEGRADE, STATUS_HS,
)
from tickets.models import (
    MaintenanceTicket, TICKET_TYPE_PREVENTIVE, TICKET_TYPE_CORRECTIVE,
    TICKET_TYPE_URGENCE, PRIORITY_BASSE, PRIORITY_MOYENNE, PRIORITY_HAUTE, PRIORITY_CRITIQUE,
    STATUS_CREE, STATUS_ASSIGNE, STATUS_EN_COURS, STATUS_RESOLU,
)
from audit.models import AuditLog


ROLES = [
    ('Admin_CNS', 'Groupe Administrateurs CNS'),
    ('Technicien_Maintenance', 'Groupe Techniciens Maintenance'),
    ('Consultant', 'Groupe Consultants'),
]

USERS = [
    {
        'username': 'admin_cns',
        'email': 'admin.cns@onda.ma',
        'first_name': 'Ahmed',
        'last_name': 'El Amrani',
        'password': 'Admin@2026!',
        'role': User.ROLE_ADMIN,
        'telephone': '+212 535 000 001',
        'service': 'Service CNS',
        'matricule': 'ONDA/CNS/001',
        'is_staff': True,
        'is_superuser': True,
    },
    {
        'username': 'tech_maint_1',
        'email': 'technicien.1@onda.ma',
        'first_name': 'Youssef',
        'last_name': 'Bennani',
        'password': 'Tech@2026!',
        'role': User.ROLE_TECHNICIAN,
        'telephone': '+212 661 111 222',
        'service': 'Maintenance Navigation',
        'matricule': 'ONDA/TECH/101',
        'is_staff': False,
    },
    {
        'username': 'tech_maint_2',
        'email': 'technicien.2@onda.ma',
        'first_name': 'Fatima',
        'last_name': 'Zahra',
        'password': 'Tech@2026!',
        'role': User.ROLE_TECHNICIAN,
        'telephone': '+212 661 333 444',
        'service': 'Maintenance Surveillance',
        'matricule': 'ONDA/TECH/102',
        'is_staff': False,
    },
    {
        'username': 'consultant_safety',
        'email': 'consultant@onda.ma',
        'first_name': 'Karim',
        'last_name': 'Tazi',
        'password': 'Cons@2026!',
        'role': User.ROLE_CONSULTANT,
        'telephone': '+212 661 555 666',
        'service': 'Sûreté/Sécurité (Audit externe)',
        'matricule': 'ONDA/CONS/201',
        'is_staff': False,
    },
]


def _seed_groups():
    groups = []
    for name, desc in ROLES:
        g, _ = Group.objects.get_or_create(name=name)
        groups.append(g)
    return groups


def _seed_users():
    created = []
    for ud in USERS:
        u, created_flag = User.objects.get_or_create(
            username=ud['username'],
            defaults={k: v for k, v in ud.items() if k != 'password'},
        )
        if created_flag or not u.check_password(ud['password']):
            u.set_password(ud['password'])
            for k, v in ud.items():
                if k not in ('password', 'username'):
                    setattr(u, k, v)
            u.save()
        created.append(u)
    return created


def _seed_equipments():
    created = {}

    vor, _ = EquipmentVOR.objects.get_or_create(
        code_unique='VOR-FES-01',
        defaults={
            'nom': 'VOR Fès Saïss (Principal)',
            'localisation_lat': 33.927,
            'localisation_lng': -4.975,
            'statut_operationnel': STATUS_OK,
            'date_mise_en_service': '2015-06-10',
            'description': 'VOR/DME installation principale approche Fès',
            'frequence': 114.70,
            'taux_modulation_AM': 30.0,
            'indice_FM': 16.0,
            'puissance_erp': 200,
            'identifiant_morse': 'FES',
        },
    )
    created['vor'] = vor

    ils_loc, _ = EquipmentILS.objects.get_or_create(
        code_unique='ILS-LOC-09',
        defaults={
            'nom': 'ILS Localizer Piste 09 Fès',
            'localisation_lat': 33.922,
            'localisation_lng': -4.969,
            'statut_operationnel': STATUS_OK,
            'date_mise_en_service': '2018-03-01',
            'description': 'Localizer Catégorie I - Piste 09',
            'type_ils': 'LOC',
            'frequence_porteuse': 110.30,
            'taux_modulation_90Hz': 20.0,
            'taux_modulation_150Hz': 20.0,
            'ddm_nominale': 0.155,
            'sdm_nominale': 0.40,
            'course': 94.0,
            'identifiant': 'IFS',
        },
    )
    created['ils_loc'] = ils_loc

    ils_gp, _ = EquipmentILS.objects.get_or_create(
        code_unique='ILS-GP-09',
        defaults={
            'nom': 'ILS Glide Path Piste 09 Fès',
            'localisation_lat': 33.929,
            'localisation_lng': -4.971,
            'statut_operationnel': STATUS_DEGRADE,
            'date_mise_en_service': '2018-03-01',
            'description': 'Glide Path Catégorie I - Seuil SDM légèrement dégradé',
            'type_ils': 'GP',
            'frequence_porteuse': 332.6,
            'taux_modulation_90Hz': 18.5,
            'taux_modulation_150Hz': 21.5,
            'ddm_nominale': 0.120,
            'sdm_nominale': 0.38,
            'course': 94.0,
            'identifiant': 'IFS',
        },
    )
    created['ils_gp'] = ils_gp

    dme, _ = EquipmentDME.objects.get_or_create(
        code_unique='DME-FES-01',
        defaults={
            'nom': 'DME associé VOR/ILS Fès',
            'localisation_lat': 33.927,
            'localisation_lng': -4.975,
            'statut_operationnel': STATUS_OK,
            'date_mise_en_service': '2015-06-10',
            'description': 'DME couplé VOR - Canal X',
            'canal': 'X',
            'numero_canal': 88,
            'frequence_interrogation': 1058.0,
            'frequence_reponse': 995.0,
            'retard_systematique': 50,
            'puissance_sortie': 1200,
            'mode_fonctionnement': 'TRACK',
            'jitter_spec': 0.5,
            'rendement_recent': 84.2,
        },
    )
    created['dme'] = dme

    dme_low, _ = EquipmentDME.objects.get_or_create(
        code_unique='DME-FES-02',
        defaults={
            'nom': 'DME Secours Fès (Rendement Faible - Alerte)',
            'localisation_lat': 33.926,
            'localisation_lng': -4.974,
            'statut_operationnel': STATUS_DEGRADE,
            'date_mise_en_service': '2012-11-20',
            'description': 'DME secours - Rendement en dessous du seuil OACI (70%)',
            'canal': 'X',
            'numero_canal': 88,
            'frequence_interrogation': 1058.0,
            'frequence_reponse': 995.0,
            'retard_systematique': 50,
            'puissance_sortie': 900,
            'mode_fonctionnement': 'SEARCH',
            'jitter_spec': 0.7,
            'rendement_recent': 68.4,
        },
    )
    created['dme_alerte'] = dme_low

    ssr, _ = EquipmentRadar.objects.get_or_create(
        code_unique='SSR-FES-01',
        defaults={
            'nom': 'Radar SSR Mode S Fès Saïss',
            'localisation_lat': 33.940,
            'localisation_lng': -4.960,
            'statut_operationnel': STATUS_OK,
            'date_mise_en_service': '2020-09-01',
            'description': 'Secondary Surveillance Radar avec Mode S et ADS-B In',
            'type_radar': 'SSR',
            'frequence_bande': 'L-Band 1030/1090 MHz',
            'portee_max': 250,
            'mode_s_actif': True,
            'traitement_oldi': True,
            'puissance_emetteur': 2.5,
        },
    )
    created['radar_ssr'] = ssr

    vcs, _ = EquipmentVCS.objects.get_or_create(
        code_unique='VCS-TOWER-01',
        defaults={
            'nom': 'Système VCS Tour de Contrôle Fès',
            'localisation_lat': 33.930,
            'localisation_lng': -4.972,
            'statut_operationnel': STATUS_OK,
            'date_mise_en_service': '2022-01-15',
            'description': 'Voice Communication System - VoIP ED-137 - Tour',
            'site_radio': 'Site Radio Aéroport Fès',
            'codec': 'G.711A',
            'protocole': 'ED-137',
            'canaux_vhf': 8,
            'voip_active': True,
            'adresse_ip': '10.10.20.10',
        },
    )
    created['vcs'] = vcs

    return created


def _seed_measurement_logs(equipments):
    MeasurementLog.objects.all().delete()
    ils_loc = equipments['ils_loc']
    ils_gp = equipments['ils_gp']
    dme = equipments['dme']
    dme_alerte = equipments['dme_alerte']

    today = timezone.now().date()
    base_ddm = ils_loc.ddm_nominale
    for j in range(7):
        d = today - timedelta(days=6 - j)
        for hour in (8, 14, 20):
            ts = timezone.make_aware(timezone.datetime.combine(d, timezone.datetime.min.time())) + timedelta(hours=hour)
            delta = 0.003 * ((j + hour) % 5 - 2)
            MeasurementLog.objects.create(
                equipment_type='EquipmentILS', equipment_id=ils_loc.pk,
                date_mesure=ts, parametre='DDM',
                valeur=round(base_ddm + delta, 4), unite='DDM',
                commentaire=f'Mesure LOC axe #{hour}',
            )
            MeasurementLog.objects.create(
                equipment_type='EquipmentILS', equipment_id=ils_gp.pk,
                date_mesure=ts, parametre='DDM',
                valeur=round(ils_gp.ddm_nominale + delta / 2, 4), unite='DDM',
            )
    for j in range(7):
        d = today - timedelta(days=6 - j)
        MeasurementLog.objects.create(
            equipment_type='EquipmentDME', equipment_id=dme.pk,
            date_mesure=timezone.make_aware(timezone.datetime.combine(d, timezone.datetime.min.time())) + timedelta(hours=10),
            parametre='RENDREMENT',
            valeur=round(85 + ((j * 1.2) % 5) - 2, 2),
            unite='%',
            commentaire='Rendement quotidien DME principal',
        )
        MeasurementLog.objects.create(
            equipment_type='EquipmentDME', equipment_id=dme_alerte.pk,
            date_mesure=timezone.make_aware(timezone.datetime.combine(d, timezone.datetime.min.time())) + timedelta(hours=10),
            parametre='RENDREMENT',
            valeur=round(68 + ((j * 0.7) % 3) - 1, 2),
            unite='%',
            commentaire='Rendement DME secours - Sous seuil OACI',
        )


def _seed_tickets(equipments, users):
    MaintenanceTicket.objects.all().delete()

    admin = next(u for u in users if u.username == 'admin_cns')
    tech1 = next(u for u in users if u.username == 'tech_maint_1')
    tech2 = next(u for u in users if u.username == 'tech_maint_2')

    ct_ils = ContentType.objects.get_for_model(EquipmentILS)
    ct_dme = ContentType.objects.get_for_model(EquipmentDME)
    ct_vor = ContentType.objects.get_for_model(EquipmentVOR)
    ct_radar = ContentType.objects.get_for_model(EquipmentRadar)

    t1 = MaintenanceTicket.objects.create(
        titre='Maintenance Préventive ILS Localizer Piste 09',
        description='Contrôle annuel IAW Programme ONDA NSM - Vérification complète Localizer.',
        type_ticket=TICKET_TYPE_PREVENTIVE,
        priorite=PRIORITY_HAUTE,
        statut=STATUS_EN_COURS,
        content_type=ct_ils,
        object_id=equipments['ils_loc'].pk,
        cree_par=admin,
        assigne_a=tech1,
        rapport_intervention=None,
    )
    t1.historique.create(action='CREATION', utilisateur=admin, commentaire='Ticket créé dans le cadre du MP annuel.')
    t1.historique.create(action='ASSIGNATION', utilisateur=admin, commentaire=f'Assigné à {tech1}', nouvelle_valeur=str(tech1))
    t1.historique.create(action='CHANGEMENT_STATUT', utilisateur=tech1, commentaire='Début intervention',
                         ancienne_valeur=STATUS_ASSIGNE, nouvelle_valeur=STATUS_EN_COURS)

    t2 = MaintenanceTicket.objects.create(
        titre='Alerte: Rendement DME secours inférieur à 70%',
        description='Seuil OACI non respecté sur DME-FES-02 - Vérifier chaîne émission/réception et alignement.',
        type_ticket=TICKET_TYPE_URGENCE,
        priorite=PRIORITY_CRITIQUE,
        statut=STATUS_ASSIGNE,
        content_type=ct_dme,
        object_id=equipments['dme_alerte'].pk,
        cree_par=admin,
        assigne_a=tech2,
    )
    t2.historique.create(action='CREATION', utilisateur=admin, commentaire='Alerte seuil OACI - Rendement DME')
    t2.historique.create(action='ASSIGNATION', utilisateur=admin, commentaire=f'Assigné à {tech2} (Expert DME)', nouvelle_valeur=str(tech2))

    t3 = MaintenanceTicket.objects.create(
        titre='Maintenance Préventive VOR Fès',
        description='Mesure routine alignement radial, identifiant Morse et BITE.',
        type_ticket=TICKET_TYPE_PREVENTIVE,
        priorite=PRIORITY_MOYENNE,
        statut=STATUS_RESOLU,
        content_type=ct_vor,
        object_id=equipments['vor'].pk,
        cree_par=admin,
        assigne_a=tech1,
        rapport_intervention=(
            'MP VOR réalisée le 20/08. Tous les paramètres dans tolérances: '
            'Mod AM=29.8%, Indice FM=15.9, Puissance ERP=198W. Identifiant Morse FES OK.'
        ),
    )
    t3.historique.create(action='CHANGEMENT_STATUT', utilisateur=admin, commentaire='MP résolue - rapport signé',
                         ancienne_valeur=STATUS_EN_COURS, nouvelle_valeur=STATUS_RESOLU)

    t4 = MaintenanceTicket.objects.create(
        titre='Correctif: Traitement OLDI Radar SSR intermittent',
        description='Pertes de messages OLDI vers contrôleur ARA - Investiguer processeur radar.',
        type_ticket=TICKET_TYPE_CORRECTIVE,
        priorite=PRIORITY_HAUTE,
        statut=STATUS_CREE,
        content_type=ct_radar,
        object_id=equipments['radar_ssr'].pk,
        cree_par=tech2,
    )
    t4.historique.create(action='CREATION', utilisateur=tech2,
                         commentaire='Ticket remonté par Tour Contrôle - Trafic heure de pointe.')


class Command(BaseCommand):
    help = 'Initialise la base avec des données de démonstration GMAO CNS'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Supprime les anciens utilisateurs/équipements/tickets avant')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Initialisation GMAO CNS (ONDA Fès) ==='))

        if options['reset']:
            self.stdout.write(self.style.WARNING('Reset demandé - purge données existantes...'))
            MaintenanceTicket.objects.all().delete()
            ChecklistItem = None
            from tickets.models import ChecklistItem, TicketHistorique
            ChecklistItem.objects.all().delete()
            TicketHistorique.objects.all().delete()
            MeasurementLog.objects.all().delete()
            for m in (EquipmentVCS, EquipmentRadar, EquipmentDME, EquipmentILS, EquipmentVOR):
                m.objects.all().delete()
            AuditLog.objects.all().delete()
            User.objects.filter(role__isnull=False).exclude(is_superuser=True).delete()

        self.stdout.write('- Groupes...')
        _seed_groups()
        self.stdout.write('- Utilisateurs...')
        users = _seed_users()
        self.stdout.write('- Équipements CNS...')
        equipments = _seed_equipments()
        self.stdout.write('- Mesures physiques (7 jours)...')
        _seed_measurement_logs(equipments)
        self.stdout.write('- Tickets & Checklists dynamiques...')
        _seed_tickets(equipments, users)

        self.stdout.write(self.style.SUCCESS('Données de démo chargées avec succès !'))
        self.stdout.write(self.style.WARNING('Identifiants par défaut :'))
        self.stdout.write('  - Admin CNS : admin_cns / Admin@2026!')
        self.stdout.write('  - Technicien : tech_maint_1 / Tech@2026!')
        self.stdout.write('  - Consultant : consultant_safety / Cons@2026!')
