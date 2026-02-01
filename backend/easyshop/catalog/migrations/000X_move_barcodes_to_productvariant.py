from django.db import migrations, models

def move_barcodes_to_productvariant(apps, schema_editor):
    Barcodes = apps.get_model('catalog', 'Barcodes')
    ProductVariant = apps.get_model('catalog', 'ProductVariant')

    for barcode in Barcodes.objects.all():
        if barcode.content_type.model == 'productvariant':
            variant = ProductVariant.objects.filter(pk=barcode.object_id).first()
            if variant:
                variant.barcode = barcode.barcode
                variant.save()

class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0023_rename_reference_id_barcodes_object_id_and_more'),  # Replace with the last migration file
    ]

    operations = [
        migrations.AddField(
            model_name='productvariant',
            name='barcode',
            field=models.CharField(max_length=100, blank=True, null=True),
        ),
        migrations.RunPython(move_barcodes_to_productvariant),
        migrations.DeleteModel(
            name='Barcodes',
        ),
    ]
