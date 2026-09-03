from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class RegistrationForm(FlaskForm):
    user_id = StringField("User ID", validators=[DataRequired(), Length(max=20)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=254)])
    name = StringField("Name", validators=[DataRequired(), Length(max=25)])
    department = StringField("Department", validators=[DataRequired(), Length(max=3)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Register")


class OTPForm(FlaskForm):
    otp = StringField("Verification code", validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField("Verify")