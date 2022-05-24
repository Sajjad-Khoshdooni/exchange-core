
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0050_customtoken'),
    ]

    operations = [
        migrations.AlterField(
            model_name='verificationcode',
            name='scope',
            field=models.CharField(choices=[('forget', 'forget'), ('verify', 'verify'), ('withdraw', 'withdraw'), ('tel', 'tel'), ('change_pass', 'change_pass'), ('change_phone', 'change_phone'), ('email_verify', 'email_verify')], max_length=32),
        ),
    ]
