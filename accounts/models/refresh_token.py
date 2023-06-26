from django.db import models


class RefreshToken(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    token = models.CharField(max_length=250, unique=True, db_index=True)

    def log_out(self):
        from rest_framework_simplejwt.tokens import RefreshToken as JWTRefreshToken

        try:
            JWTRefreshToken(self.token).blacklist()
            # Handle
        except Exception:
            # Handle the case when the refresh token is already expired or invalid
            pass
