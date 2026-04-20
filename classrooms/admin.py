from django.contrib import admin

from .models import Classroom, ClassroomMembership


class MembershipInline(admin.TabularInline):
    model = ClassroomMembership
    extra = 1


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ['name', 'language', 'created_by', 'created_at']
    inlines = [MembershipInline]


@admin.register(ClassroomMembership)
class ClassroomMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'classroom', 'role', 'joined_at']
    list_filter = ['role', 'classroom']
