from django.db import migrations

def fix_course_module_slugs(apps, schema_editor):
    CourseModule = apps.get_model('accounts_app', 'CourseModule')

    # Web Dev modules: IDs 1 to 10, module_number 1 to 10
    for m_id in range(1, 11):
        CourseModule.objects.filter(pk=m_id).update(course_slug='web-development', module_number=m_id, order=m_id)

    # Digital Marketing modules: IDs 11 to 23, module_number 1 to 13
    for idx, m_id in enumerate(range(11, 24), 1):
        CourseModule.objects.filter(pk=m_id).update(course_slug='digital-marketing', module_number=idx, order=idx)

def reverse_func(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('accounts_app', '0012_liveclassschedule_recorded_at_and_more'),
    ]

    operations = [
        migrations.RunPython(fix_course_module_slugs, reverse_func),
    ]
