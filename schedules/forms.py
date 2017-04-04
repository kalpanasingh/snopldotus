from django import forms

import datetime

class ScheduleForm(forms.Form):
    start_date = forms.DateField(
        label='Schedule start date (YYYY-MM-DD)',
        initial=datetime.date.today
    )

    end_date = forms.DateField(
        label='Schedule ending date (YYYY-MM-DD)',
        initial=(lambda: datetime.date.today() + datetime.timedelta(weeks=1))
    )

    notes = forms.CharField(max_length=1000, label='Notes', required=False)
    docfile = forms.FileField(label='Schedule PDF file')

