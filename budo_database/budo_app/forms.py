from Django import forms


class CheckInForm(forms.Form):
    check_in_date = forms.DateField(null=True, default=None)


# <p><label for="check_in_date">Check-In Datum</label><input type="date" id="check_in_date" value="{{today_date}}"></p>
# <p><label for="ausweis">Ausweis</label><input type="checkbox" id="ausweis"></p>
# <p><label for="e-card">E-Card</label><input type="checkbox" id="e-card"></p>
# <p><label for="covid">Covid Test-Erlaubnis</label><input type="checkbox" name="Covid" id="covid"></p>
# <p><label for="einverstaendnis">Einverständniserklärung</label><input type="checkbox" name="" id="einverstaendnis"></p>
# <p><label for="taschengeld">Taschengeld </label><input type="text" name="" id="taschengeld"></p>
