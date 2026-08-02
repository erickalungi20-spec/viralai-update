from pyngrok import ngrok

t = ngrok.connect(8000, bind_tls=True)
print(t.public_url)
