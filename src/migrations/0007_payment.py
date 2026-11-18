"""Payments: a record of what was received for the tasks of a period.

Adds the Payment model and the task's link to it (empty = not paid).
Existing tasks start unpaid. Reversible.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0006_task_external_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="Payment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("period_start", models.DateField(verbose_name="início do período")),
                ("period_end", models.DateField(verbose_name="fim do período")),
                (
                    "estimated_usd",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=12,
                        verbose_name="valor estimado (US$)",
                    ),
                ),
                (
                    "estimated_brl",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=12,
                        null=True,
                        verbose_name="valor estimado (R$)",
                    ),
                ),
                (
                    "paid_usd",
                    models.DecimalField(
                        decimal_places=2, max_digits=12, verbose_name="valor pago (US$)"
                    ),
                ),
                (
                    "paid_brl",
                    models.DecimalField(
                        decimal_places=2, max_digits=12, verbose_name="valor pago (R$)"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="registrado em"
                    ),
                ),
            ],
            options={
                "verbose_name": "pagamento",
                "verbose_name_plural": "pagamentos",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="task",
            name="payment",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tasks",
                to="tasks.payment",
                verbose_name="pagamento",
            ),
        ),
    ]
