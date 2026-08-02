from pyngrok import ngrok\n\nt = ngrok.connect(8000, bind_tls=True)\nprint(t.public_url)\n
