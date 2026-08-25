from django.contrib import admin
from .models import MaintenanceTicket, ChecklistItem, TicketHistorique


class ChecklistItemInline(admin.TabularInline):
    model = ChecklistItem
    extra = 0
    fields = ('libelle', 'est_effectue', 'ordre', 'commentaire')


class TicketHistoriqueInline(admin.TabularInline):
    model = TicketHistorique
    extra = 0
    fields = ('action', 'utilisateur', 'date', 'ancienne_valeur', 'nouvelle_valeur', 'commentaire')
    readonly_fields = ('date',)


@admin.register(MaintenanceTicket)
class MaintenanceTicketAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'titre', 'type_ticket', 'priorite', 'statut',
        'assigne_a', 'cree_par', 'date_creation',
    )
    list_filter = ('type_ticket', 'priorite', 'statut', 'content_type')
    search_fields = ('titre', 'description', 'rapport_intervention')
    raw_id_fields = ('cree_par', 'assigne_a')
    readonly_fields = ('date_creation', 'date_modification')
    inlines = [ChecklistItemInline, TicketHistoriqueInline]
    fieldsets = (
        (None, {'fields': ('titre', 'description', 'type_ticket', 'priorite', 'statut')}),
        ('Équipement', {'fields': ('content_type', 'object_id')}),
        ('Acteurs', {'fields': ('cree_par', 'assigne_a')}),
        ('Dates', {'fields': ('date_creation', 'date_modification', 'date_cloture')}),
        ('Rapport', {'fields': ('rapport_intervention',)}),
    )


@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'libelle', 'est_effectue', 'ordre')
    list_filter = ('est_effectue',)
    search_fields = ('libelle', 'commentaire')


@admin.register(TicketHistorique)
class TicketHistoriqueAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'action', 'utilisateur', 'date')
    list_filter = ('action',)
    search_fields = ('commentaire',)
    readonly_fields = ('date',)
