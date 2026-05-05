from django.db import models

class IdSequence(models.Model):
    key = models.CharField(max_length=255, primary_key=True)
    last_issued = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'id_generator_sequence'
    
    def __str__(self):
        return f"{self.key} @ {self.last_issued}"