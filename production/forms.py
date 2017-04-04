from django import forms
from django.core.exceptions import ValidationError

import string
import copy
import re


def validate_macros(values):
    '''Validate a macro is .mac file, is small (for reading)
    and contains only the expected string templates.
    '''
    # Permitted template strings
    templates = ["z", "radius", "day", "rate"]

    # Loop through each file
    for value in values:
        if not value.name.endswith('mac'):
            raise ValidationError('Only .mac files allowed')
        if value.size > 1024*1024: # MB
            raise ValidationError('File sizes too large!')
        macro_text = value.read()
        # Ensure that there are no extra template strings
        template = string.Template(macro_text)
        try:
            template.substitute(dict((key, 0) for key in templates))
        except KeyError, e:
            raise ValidationError('Macro contains invalid template: {0}'.format(e))
        # Ensure that no rate is set
        p = '/generator/rat/set\s*(\d+)'
        for line in macro_text.splitlines():
            if re.match(p, line) is not None:
                raise ValidationError("Macro cannot set number of events")
        # Return cursor to beginning
        value.seek(0)


class BenchmarkingForm(forms.Form):
    name = forms.CharField(max_length=100, label="Name (requested by):")
    descriptor = forms.CharField(max_length=100, label="Descriptor (e.g. phase):")
    attachments = forms.FileField(label = "Files (multiple possible)",
                                  widget=forms.ClearableFileInput(attrs={'multiple': True}))
    rat_version = forms.ChoiceField(widget = forms.Select())
    commit_hash = forms.CharField(max_length=30, label="Commit hash (optional)", required=False)

    def __init__(self, versions, *args, **kwargs):
        '''Override constructor to dynamically populate drop-down entries
        '''        
        super(BenchmarkingForm, self).__init__(*args, **kwargs)
        self.fields["rat_version"].choices = [(v, v) for v in versions]

    def clean(self):
        '''Add the validator here for files (if added as a validator to the field then only one
        file is ever handled, here we can do multiple).
        '''
        try:
            validate_macros(self.files.getlist("attachments"))
        except AttributeError, e:
            pass # Missing the field, will be caught by the form
        return self.cleaned_data


class ResultsForm(forms.Form):
    
    version = forms.ChoiceField(widget = forms.Select())
    phase = forms.ChoiceField(widget = forms.Select(),
                              required = False)

    def __init__(self, versions, phases, default_phase, *args, **kwargs):
        '''Override constructor to dynamically populate drop-down entries
        '''
        super(ResultsForm, self).__init__(*args, **kwargs)
        self.fields['version'].choices = [('None', '...')] + [(v, v) for v in versions]
        self.fields['phase'].choices = [('None', '...')] + [(v, v) for v in phases]


class MacroForm(forms.Form):
    phase = forms.CharField(widget=forms.HiddenInput())
    macro = forms.CharField(widget=forms.HiddenInput())
    size = forms.FloatField(widget=forms.HiddenInput())
    time = forms.FloatField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        # There're better ways to get templates across than tacking on to initial
        # But would probably require overriding mode methods in the formset
        super(MacroForm, self).__init__(*args, **kwargs)
        if 'initial' in kwargs:
            self.from_data = False
            self.templates = kwargs['initial'].pop('templates', [])
            for t in self.templates:
                self.fields[t] = forms.CharField(max_length=100)
        else:
            self.from_data = True
            self.templates = []
            # Repopulate the templates
            for key, val in kwargs['data'].iteritems():
                if key.startswith(self.prefix):
                    name = key[len(self.prefix)+1:]
                    if name not in self.fields and name != "template_names":
                        self.fields[name] = forms.CharField(max_length=100)
                        self.fields[name].initial = val
                        self.templates.append(name)
 
    def template_fields(self):
        fields = []
        names = []
        for field in self:
            if field.name in self.templates:
                if field.name != 'rate' or self.rate_template is True:
                    names.append(field.name)
                    fields.append(field)
        return fields

    def visible_fields(self):
        fields = super(MacroForm, self).visible_fields()
        visible_fields = []
        names = []
        for field in fields:
            if field.name not in self.templates:
                visible_fields.append(field)
                names.append(field.name)
            elif field.name == 'rate' and self.rate_template is False:
                visible_fields.append(field)
                names.append(field.name)
        return visible_fields


class MacroFormByTime(MacroForm):
    fixed_rate = forms.BooleanField(widget=forms.HiddenInput(), required=False) # This seems stupid - form fails if value is false and required is false
    # Use char fields for rate and n_events in case the values are "FIXED"
    rate = forms.CharField()
    n_events = forms.CharField(widget=forms.TextInput(attrs={'class': 'request_tg'}))
    n_runs = forms.IntegerField(required=True)

    def __init__(self, *args, **kwargs):        
        super(MacroFormByTime, self).__init__(*args, **kwargs)
        self.rate_template = False
        if 'initial' in kwargs:
            self.fixed_rate = kwargs['initial']['fixed_rate']
        else:
            self.fixed_rate = (kwargs['data']['{0}-fixed_rate'.format(self.prefix)]=='True')
        if self.fixed_rate is True:
            # Hide inputs and just show that the rate is fixed
            self.fields['rate'].widget = forms.HiddenInput()
            self.fields['n_events'].widget = forms.HiddenInput()
            self.fields['rate'].initial = "FIXED"
            self.fields['n_events'].initial = "FIXED"
            self.fields['fixed_rate'].initial = True
            self.hidden_keys = ["phase", "macro", "size", "time", "rate", "n_events"]
        else:
            # User can only enter requested number of events
            # Show the rate, but make it read only
            self.fields['n_runs'].widget.attrs['readonly'] = True
            self.fields['rate'].widget.attrs['readonly'] = True
            self.fields['fixed_rate'].initial = False
            self.hidden_keys = ["phase", "macro", "size", "time"]

    def hidden_tabs(self):
        return [self[k].value() for k in self.hidden_keys]


class MacroFormByNumber(MacroForm):
    ev_per_run = forms.IntegerField(widget=forms.HiddenInput())
    n_events = forms.FloatField(widget=forms.TextInput(attrs={'class': 'request_tg'})) # to allow exponents
    n_runs = forms.IntegerField(required=True)

    def __init__(self, *args, **kwargs):
        super(MacroFormByNumber, self).__init__(*args, **kwargs)
        self.rate_template = True
        self.fields['n_runs'].widget.attrs['readonly'] = True
        if 'initial' in kwargs:
            # Find the lowest number of events pery run from either the size or time information
            # Have to assume the initial values are passed to the constructor        
            max_ev_size = 1024 * 1024.0 / kwargs['initial']['size'] # 1 GB max file size, kB ev size
            max_ev_time = 3600 * 20.0 / kwargs['initial']['time'] # 20 hr max run, ev s time
        else:
            max_ev_size = 1024 * 1024.0 / float(self['size'].value())
            max_ev_time = 1024 * 1024.0 / float(self['size'].value())
        if max_ev_size < max_ev_time:
            max_ev_run = max_ev_size
        else:
            max_ev_run = max_ev_time
            # If # > 20k then floor to nearest 10k
        if max_ev_run > 10000:
            max_ev_run = int(max_ev_run) / 10000 * 10000
        else:
            max_ev_run = int(max_ev_run)
        self.fields['ev_per_run'].initial = max_ev_run

    def hidden_tabs(self):
        return [self["phase"].value(),
                self["macro"].value(),
                self["size"].value(),
                self["time"].value(),
                self["ev_per_run"].value()]


class BaseRequestFormset(forms.formsets.BaseFormSet):

    def __init__(self, macro_keys = [], *args, **kwargs):
        self.macro_keys = macro_keys
        super(BaseRequestFormset, self).__init__(*args, **kwargs)
        
    def add_prefix(self, index):
        '''Override to make splitting easier
        '''
        if not len(self.macro_keys):
            return '{0}_{1}'.format(self.prefix, index)
        else:
            return self.macro_keys[index]
