# Heart Disease Prediction System

A machine learning-powered Flask web application that predicts heart disease risk using patient health parameters.

## Features

- 🔐 User authentication (Local + Google OAuth)
- 💓 Heart disease risk prediction using Random Forest ML model
- 📊 Prediction history with MongoDB storage
- 📈 Risk analysis and model performance analytics
- 👤 User profile with statistics
- 🎨 Beautiful responsive UI with Bootstrap

## Tech Stack

- **Backend**: Flask, Python
- **Database**: MongoDB Atlas
- **ML Model**: Scikit-learn Random Forest
- **Frontend**: Bootstrap 5, Chart.js
- **Deployment**: Vercel

## Local Setup

### Prerequisites
- Python 3.8+
- MongoDB Atlas account
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd heart_app_starter
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your MongoDB and Google OAuth credentials
   ```

5. **Run the application**
   ```bash
   python app.py
   ```
   Visit `http://localhost:5000`

## Deployment to Vercel

### Prerequisites
- Vercel account
- MongoDB Atlas connection string
- Google OAuth credentials

### Steps

1. **Install Vercel CLI**
   ```bash
   npm i -g vercel
   ```

2. **Set environment variables in Vercel**
   ```bash
   vercel env add MONGO_URI
   vercel env add GOOGLE_CLIENT_ID
   vercel env add GOOGLE_CLIENT_SECRET
   vercel env add SECRET_KEY
   ```

3. **Deploy**
   ```bash
   vercel --prod
   ```

4. **Update Google OAuth redirect URIs**
   - Add your Vercel deployment URL to Google OAuth settings
   - Format: `https://your-app.vercel.app/login/google/callback`

## API Routes

### Authentication
- `POST /register` - User registration
- `POST /login` - User login
- `GET /logout` - User logout
- `GET /login/google` - Google OAuth login
- `GET /login/google/callback` - Google OAuth callback

### Prediction
- `GET/POST /predict` - Make heart disease prediction
- `GET /history` - View prediction history
- `GET /risk_analysis` - View risk analysis
- `GET /model_performance` - View model metrics
- `GET /profile` - View user profile

## Database Schema

### Users Collection
```json
{
  "_id": ObjectId,
  "username": "string",
  "password": "string"
}
```

### Predictions Collection
```json
{
  "_id": ObjectId,
  "username": "string",
  "timestamp": "datetime",
  "features": {
    "age": "float",
    "sex": "float",
    "cp": "float",
    "trestbps": "float",
    "chol": "float",
    "fbs": "float",
    "restecg": "float",
    "thalach": "float",
    "exang": "float",
    "oldpeak": "float",
    "slope": "float",
    "ca": "float",
    "thal": "float"
  },
  "prediction_result": "int" // 0 = Low Risk, 1 = High Risk
}
```

## Model Information

- **Algorithm**: Random Forest Classifier
- **Accuracy**: 92%
- **Training Data**: UCI Heart Disease Dataset (297 samples)
- **Features**: 13 health parameters
- **Output**: Binary classification (0 = Low Risk, 1 = High Risk)

## Security Notes

⚠️ **Important for Production:**
- Change the Flask secret key
- Use bcrypt or similar for password hashing
- Enable MongoDB IP whitelist
- Store secrets in environment variables only
- Use HTTPS only for OAuth redirects

## Troubleshooting

### 500 Error on Vercel
- Check that `api/index.py` exists
- Verify environment variables are set
- Check Vercel logs: `vercel logs`

### MongoDB Connection Issues
- Verify connection string in `.env`
- Check IP whitelist in MongoDB Atlas
- Ensure database and collections exist

### Model Loading Issues
- Verify `heart_disease_model.pkl` exists
- Ensure scikit-learn version matches training environment

## File Structure

```
heart_app_starter/
├── api/
│   └── index.py           # Vercel serverless function entry point
├── static/
│   └── css/
│       └── style.css
├── templates/
│   ├── landing.html
│   ├── login.html
│   ├── register.html
│   ├── index.html
│   ├── predict.html
│   ├── result.html
│   ├── history.html
│   ├── risk_analysis.html
│   ├── model_performance.html
│   └── profile.html
├── app.py                 # Local Flask application
├── train_model.py         # Model training script
├── heart.csv              # Training dataset
├── heart_disease_model.pkl # Trained model
├── requirements.txt       # Python dependencies
├── vercel.json            # Vercel configuration
└── .env.example           # Environment variables template
```

## Future Enhancements

- [ ] User email verification
- [ ] Password reset functionality
- [ ] Prediction export as PDF/CSV
- [ ] Medical provider integration
- [ ] Advanced analytics dashboard
- [ ] Multi-language support
- [ ] Mobile app version

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.
