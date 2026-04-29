from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=_env_path, override=True)


from api.Controllers.User.UserGet import user_get_bp
from api.Controllers.User.UserCreate import user_create_bp
from api.Controllers.User.UserUpdate import user_update_bp
from api.Controllers.User.UserDelete import user_delete_bp
from api.Controllers.User.UserLogin import user_login_bp
from api.Controllers.User.UserAvatar import user_avatar_bp
from api.Controllers.Video.VideoUpload import video_upload_bp
from api.Controllers.Video.OriginalsActivity import originals_activity_bp
from api.Controllers.Notifications.NotificationsController import notifications_bp
from api.Controllers.Global.TableCount import table_count_bp
from api.Payment.stripe import stripe_payment_bp

from api.Controllers.Pelis.PeliGet import peli_get_bp
from api.Controllers.Pelis.PeliCreate import peli_create_bp
from api.Controllers.Pelis.PeliUpdate import peli_update_bp
from api.Controllers.Pelis.PeliDelete import peli_delete_bp

from api.Controllers.Series.SerieGet import serie_get_bp
from api.Controllers.Series.SerieCreate import serie_create_bp
from api.Controllers.Series.SerieUpdate import serie_update_bp
from api.Controllers.Series.SerieDelete import serie_delete_bp
from api.Controllers.Favorites.FavoritesController import favorites_bp
from api.Controllers.Watchlist.WatchlistController import watchlist_bp
from api.Controllers.SeguirViendo.SeguirViendoController import seguir_viendo_bp
from api.Controllers.Historial.HistorialController import historial_bp
from api.Controllers.LlistaOriginals.LlistaOriginalsController import llista_originals_bp

from sqlalchemy import text
from api.Models.Base import engine, Base
from api.Models.User import User
from api.Models.Peli import Peli
from api.Models.Serie import Serie
from api.Models.Video import Video
from api.Models.Favorite import Favorite
from api.Models.Watchlist import Watchlist
from api.Models.SeguirViendo import SeguirViendo
from api.Models.HistorialVisualitzacio import HistorialVisualitzacio
from api.Models.LlistaOriginals import LlistaOriginals

# Crear taules si no existeixen
Base.metadata.create_all(bind=engine)

app = Flask(__name__)
CORS(app)

app.register_blueprint(user_get_bp)
app.register_blueprint(user_create_bp)
app.register_blueprint(user_update_bp)
app.register_blueprint(user_delete_bp)
app.register_blueprint(user_login_bp)
app.register_blueprint(user_avatar_bp)
app.register_blueprint(video_upload_bp)
app.register_blueprint(originals_activity_bp)
app.register_blueprint(notifications_bp)
app.register_blueprint(table_count_bp)
app.register_blueprint(stripe_payment_bp, url_prefix='/api')

app.register_blueprint(peli_get_bp)
app.register_blueprint(peli_create_bp)
app.register_blueprint(peli_update_bp)
app.register_blueprint(peli_delete_bp)

app.register_blueprint(serie_get_bp)
app.register_blueprint(serie_create_bp)
app.register_blueprint(serie_update_bp)
app.register_blueprint(serie_delete_bp)
app.register_blueprint(favorites_bp)
app.register_blueprint(watchlist_bp)
app.register_blueprint(seguir_viendo_bp)
app.register_blueprint(historial_bp)
app.register_blueprint(llista_originals_bp)

if __name__ == "__main__":
    app.run(debug=True)
