from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):

        user = super().populate_user(request, sociallogin, data)
        
        if not getattr(user, 'full_name', None):
            first_name = data.get('first_name') or ''
            last_name = data.get('last_name') or ''
            name = data.get('name') or ''
            
            if name:
                user.full_name = name
            elif first_name or last_name:
                user.full_name = f"{first_name} {last_name}".strip()
            else:
                user.full_name = user.email.split('@')[0]
                
        return user
