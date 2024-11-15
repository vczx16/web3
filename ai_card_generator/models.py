from django.db import models

class Card(models.Model):
    RARITY_CHOICES = [
        ('C', 'Common'),
        ('R', 'Rare'),
        ('SR', 'Super Rare'),
        ('SSR', 'Super Super Rare'),
    ]

    TYPE_CHOICES = [
        ('NORMAL', 'Normal'),
        ('FIRE', 'Fire'),
        ('WATER', 'Water'),
        ('GRASS', 'Grass'),
        ('ELECTRIC', 'Electric'),
        ('PSYCHIC', 'Psychic'),
        ('FIGHTING', 'Fighting'),
        ('DRAGON', 'Dragon'),
        ('DARK', 'Dark'),
        ('STEEL', 'Steel'),
        ('FAIRY', 'Fairy'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='cards/')
    created_at = models.DateTimeField(auto_now_add=True)
    rarity = models.CharField(max_length=3, choices=RARITY_CHOICES, default='C')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='NORMAL')
    attack = models.IntegerField(default=100)
    defense = models.IntegerField(default=100)
    prompt = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'ai_card_generator_card'  # 显式指定表名
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.rarity})"