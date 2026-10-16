from django import forms

from farms.models import Animal


class AskForm(forms.Form):
    animal = forms.ModelChoiceField(Animal.objects.none(), required=False, label="Животное",
                                    empty_label="— без привязки —")
    question = forms.CharField(label="Вопрос", min_length=3, max_length=1000,
                               widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Например: корова вялая, не ест второй день"}))

    def __init__(self, *args, animals=None, **kwargs):
        super().__init__(*args, **kwargs)
        if animals is not None:
            self.fields["animal"].queryset = animals
