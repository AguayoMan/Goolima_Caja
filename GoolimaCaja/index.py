from flask import Flask, request, render_template, redirect, url_for, flash, session, send_file, request, jsonify
from decimal import Decimal
from flask_mysqldb import MySQL
from datetime import timedelta, datetime
from collections import Counter
from flask import Flask, render_template, request
from dotenv import load_dotenv
import os
from io import BytesIO


import json
import pendulum
import secrets

load_dotenv()  # Carga las variables de entorno del archivo .env


app = Flask(__name__)



app = Flask(__name__,static_url_path='/static')


app.secret_key = secrets.token_hex(16)  # Genera una clave secreta de 16 bytes en formato hexadecimal


app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT'))  # Asegúrate de convertir el puerto a entero

mysql = MySQL(app)  # Inicializa la conexión MySQL aquí

@app.route('/buscar_usuario', methods=['POST'])
def buscar_usuario():
    usuario = request.form['usuario']
    contraseña = request.form['contraseña']
    session['user_id'] = request.form['usuario']
    session['username'] = request.form['usuario']
    
    try:
        cur = mysql.connection.cursor()
        cur.execute('''
            SELECT NombreEmpleado, TipoEmpleado 
            FROM usuarios_cat
            WHERE Usuario = %s AND Contraseña = %s and Eliminado = 0;
        ''', (usuario, contraseña))

        result = cur.fetchone()  # Para obtener un único resultado
        cur.close()

        if result:
            if result[1] == "Administrador":
                cur = mysql.connection.cursor()
                cur.execute('''
                SELECT UsuarioId,NombreEmpleado
                FROM usuarios_cat
                WHERE Usuario = %s;
                ''', (usuario,))

                result = cur.fetchone()  # Para obtener un único resultado
                cur.close()
                session['user_id']=result[0];
                session['username'] = result[1]; 
                flash('Acceso correcto como administrador', 'success')
                return redirect(url_for('Venta'))
            else:
                flash('Acceso correcto como usuario', 'success')
                return redirect(url_for('Clientes_Consultar_Venta'))   
        else:
            flash('Usuario o Contraseña incorrectas', 'danger')
            return redirect(url_for('principal'))  # Redirige a la página de inicio de sesión

    except Exception as e:
        flash(f"Error en la búsqueda de usuario: {e}", 'danger')
        return redirect(url_for('principal'))  # Redirige a la página de inicio de sesión en caso de error


#estas son las rutas o lo que se pondra en el navegador, de ahi, acceder a lo que se busca
@app.route('/')
def principal():
    return render_template('login.html')

#estas son las rutas o lo que se pondra en el navegador, de ahi, acceder a lo que se busca
@app.route('/O')
def OrdenesAdmin():
    cur = mysql.connection.cursor()
    cur.execute('''
        SELECT O.OrdenId, P.NombreProducto, OD.Precio, OD.Cantidad, OD.TotalFinal, O.totalOrden, O.Restante 
        FROM ordenes_cat AS O 
        INNER JOIN ordenes_det AS OD ON O.OrdenId = OD.OrdenId 
        INNER JOIN productos_cat AS P ON P.ProductoId = OD.ProductoId 
        WHERE O.StatusPagada = 0 
        ORDER BY O.OrdenId,P.NombreProducto;
    ''')
    data = cur.fetchall()

    # Crear un diccionario para agrupar por OrdenId
    ordenes = {}
    for row in data:
        orden_id = row[0]
        if orden_id not in ordenes:
            ordenes[orden_id] = {
                'productos': [],
                'total_orden': row[5],
                'restante': row[6],
            }
        ordenes[orden_id]['productos'].append({
            'nombre': row[1],
            'precio': row[2],
            'cantidad': row[3],
            'total_final': row[4],
        })

    # Pasar el diccionario agrupado al template
    return render_template('Ordenes.html', ordenes=ordenes)

#estas son las rutas o lo que se pondra en el navegador, de ahi, acceder a lo que se busca
@app.route('/OC')
def OrdenesAdminClientes():
    cur = mysql.connection.cursor()
    cur.execute('''
        SELECT O.OrdenId, P.NombreProducto, OD.Precio, OD.Cantidad, OD.TotalFinal, O.totalOrden, O.Restante,C.NombreCliente,C.ClienteId 
        FROM ordenes_cat AS O 
        INNER JOIN ordenes_det AS OD ON O.OrdenId = OD.OrdenId
        INNER JOIN clientes_cat AS C ON O.ClienteId = C.ClienteId 
        INNER JOIN productos_cat AS P ON P.ProductoId = OD.ProductoId 
        WHERE O.StatusPagada = 0 
        ORDER BY O.OrdenId,P.NombreProducto;
    ''')
    data = cur.fetchall()

    # Crear un diccionario para agrupar por OrdenId
    ordenes = {}
    for row in data:
        orden_id = row[0]
        if orden_id not in ordenes:
            ordenes[orden_id] = {
                'productos': [],
                'total_orden': row[5],
                'restante': row[6],
                'cliente': row[7],
                'clienteid': row[8],
            }
        ordenes[orden_id]['productos'].append({
            'nombre': row[1],
            'precio': row[2],
            'cantidad': row[3],
            'total_final': row[4],
        })

    # Pasar el diccionario agrupado al template
    return render_template('OrdenesClientesCredito.html', ordenes=ordenes)

@app.route('/deletePC/<int:orden_id>/<string:nombre_producto>/<int:cantidad>', methods=['GET'])
def delete_productoC(orden_id, nombre_producto, cantidad):
    cur = mysql.connection.cursor()
    # Actualizar la cantidad del producto y su total final en Ordenes_det
    cur.execute('''
        UPDATE productos_cat
        SET CantidadStock = CantidadStock + %s
        WHERE NombreProducto = %s
    ''', (cantidad, nombre_producto))
    # Obtener la cantidad, total actual del producto en la orden y el precio

    cur.execute('''
        SELECT OD.Cantidad, OD.TotalFinal, OD.Precio, O.totalOrden, O.Restante
        FROM ordenes_det AS OD
        INNER JOIN ordenes_cat AS O ON O.OrdenId = OD.OrdenId
        INNER JOIN productos_cat AS P ON P.ProductoId = OD.ProductoId
        WHERE O.OrdenId = %s AND P.NombreProducto = %s
    ''', (orden_id, nombre_producto))
    
    producto = cur.fetchone()

    if producto:
        cantidad_actual = producto[0]
        total_final_producto = producto[1]
        precio_producto = producto[2]
        total_orden_actual = producto[3]
        total_restante_actual = producto[4]

        # Si la cantidad a eliminar es menor que la cantidad actual, actualizar cantidad y total final
        if cantidad < cantidad_actual:
            nueva_cantidad = cantidad_actual - cantidad
            nuevo_total_final_producto = total_final_producto - (precio_producto * cantidad)

            # Actualizar la cantidad del producto y su total final en Ordenes_det
            cur.execute('''
                UPDATE ordenes_det
                SET Cantidad = %s, TotalFinal = %s
                WHERE OrdenId = %s AND ProductoId = (
                    SELECT ProductoId FROM productos_cat WHERE NombreProducto = %s LIMIT 1
                )
            ''', (nueva_cantidad, nuevo_total_final_producto, orden_id, nombre_producto))
        
        # Si la cantidad a eliminar es igual o mayor a la cantidad actual, eliminar el producto
        else:
            cur.execute('''
                DELETE FROM ordenes_det
                WHERE OrdenId = %s AND ProductoId = (
                    SELECT ProductoId FROM productos_cat WHERE NombreProducto = %s LIMIT 1
                )
            ''', (orden_id, nombre_producto))

        # Actualizar el total de la orden y el restante restando el precio total del producto eliminado
        nuevo_total_orden = total_orden_actual - (precio_producto * cantidad)
        nuevo_restante_orden = total_restante_actual - (precio_producto * cantidad)

        cur.execute('''
            UPDATE ordenes_cat
            SET totalOrden = %s, Restante = %s
            WHERE OrdenId = %s
        ''', (nuevo_total_orden, nuevo_restante_orden, orden_id))

        # Confirmar los cambios en la base de datos
        mysql.connection.commit()    

    return redirect(url_for('OrdenesAdminClientes'))




#estas son las rutas o lo que se pondra en el navegador, de ahi, acceder a lo que se busca
@app.route('/P')
def ProductosAgregarAdmin():
    return render_template('ProductosAgregar.html')



@app.route('/ProductosAgregarAdmin', methods=['POST'])
def Productos_Agregar_Admin():
    NombreProducto = request.form['NombreProducto']
    Precio = request.form['Precio']
    Venta = request.form['CostoVenta']
    Abreviatura = request.form['Abreviatura']
    CantidadStock = request.form['CantidadStock']
    
    # Convertir el valor del checkbox 'DisponibleParaDescuento' a 1 o 0
    DisponibleParaDescuento = request.form.get('DisponibleParaDescuento', '0')

    try:
        cur = mysql.connection.cursor()
        query = '''
            INSERT INTO productos_cat 
            (NombreProducto, Abreviatura, Precio, PrecioCompra, CantidadStock, DisponibleParaDescuento, Eliminado)
            VALUES (%s, %s, %s, %s, %s, %s, 0);
        '''
        cur.execute(query, (NombreProducto, Abreviatura, Precio, Venta, CantidadStock, DisponibleParaDescuento))
        mysql.connection.commit()
        cur.close()
        
        flash('Producto o servicio agregado correctamente', 'success')
        return redirect(url_for('ProductosAgregarAdmin'))
    except Exception as e:
        print(e)
        flash('Hubo un error al agregar el Producto o servicio', 'danger')
        return redirect(url_for('ProductosAgregarAdmin'))



@app.route('/ProductosEliminar')
def Productos_Eliminar():
    return render_template('ProductosEliminar.html')


@app.route('/ProductosEliminarAdminNom', methods=['POST'])
def Productos_Eliminar_Consultar_AdminNom():
    producto = request.form['NombreProducto']
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM productos_cat WHERE Eliminado = 0 and NombreProducto LIKE %s', ('%' + producto + '%',))
    data = cur.fetchall()
    return render_template('ProductosEliminar.html', data=data)

@app.route('/deleteP/<string:id>')
def deleteP_data(id):
        cur=mysql.connection.cursor()
        cur.execute('UPDATE productos_cat SET Eliminado = 1 WHERE Eliminado = 0 AND ProductoId = %s', (id,))
        mysql.connection.commit()
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM productos_cat where Eliminado = 0;')
        data = cur.fetchall() 
        return render_template('ProductosEliminar.html',data=data)

@app.route('/BuscarEditarProducto/<string:id>')
def BuscarEditarProducto_data(id):
        cur=mysql.connection.cursor()
        cur.execute('SELECT * FROM productos_cat where Eliminado = 0 and ProductoId = %s', (id,))
        data = cur.fetchall() 
        return render_template('ProductosEditar.html',data=data)

@app.route('/updateP/<string:id>', methods=['POST'])
def updateP_data(id):
    NombreProducto = request.form['NombreProducto']
    Precio = request.form['Precio']
    Abreviatura = request.form['Abreviatura']
    CantidadStock = request.form['CantidadStock']
    DisponibleParaDescuento = request.form['DisponibleParaDescuento']
    cur = mysql.connection.cursor()
    try:
        cur.execute('UPDATE productos_cat SET NombreProducto = %s, Precio = %s, Abreviatura = %s, CantidadStock = %s, DisponibleParaDescuento = %s WHERE ProductoId = %s', (NombreProducto,Precio, Abreviatura, CantidadStock,DisponibleParaDescuento, id))
        mysql.connection.commit()
        flash('Producto actualizado correctamente', 'success')
    except Exception as e:
        flash('Error al actualizar el Producto: {}'.format(str(e)), 'danger')
    finally:
        cur.close()
    return redirect(url_for('Productos_Eliminar'))          

#estas son las rutas o lo que se pondra en el navegador, de ahi, acceder a lo que se busca
@app.route('/U')
def UsuariosAgregarAdmin():
    return render_template('UsuariosAgregar.html')


@app.route('/UsuariosAgregarAdmin', methods=['POST'])
def Usuarios_Agregar_Admin():
    NombreEmpleado = request.form['NombreEmpleado']
    Usuario = request.form['Usuario']
    Contraseña = request.form['Contraseña']
    TipoEmpleado = request.form['TipoEmpleado']

    try:
        cur = mysql.connection.cursor()
        query = '''
            insert into usuarios_cat (NombreEmpleado,Usuario, Contraseña, TipoEmpleado,Eliminado)
            values(%s,%s,%s,%s,0);
        '''
        cur.execute(query, (NombreEmpleado,Usuario, Contraseña, TipoEmpleado))
        mysql.connection.commit()
        cur.close()
        
        flash('Usuario agregado correctamente', 'success')
        return redirect(url_for('UsuariosAgregarAdmin'))
    except Exception as e:
        print(e)
        flash('Hubo un error al agregar al usuario', 'danger')
        return redirect(url_for('UsuariosAgregarAdmin'))


@app.route('/UsuariosEliminar')
def Usuarios_Eliminar():
    return render_template('UsuariosEliminar.html')

@app.route('/deleteU/<string:id>')
def deleteU_data(id):
        cur=mysql.connection.cursor()
        cur.execute('UPDATE usuarios_cat SET Eliminado = 1 WHERE Eliminado = 0 AND UsuarioId = %s', (id,))
        mysql.connection.commit()
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM usuarios_cat where Eliminado = 0;')
        data = cur.fetchall() 
        return render_template('UsuariosEliminar.html',data=data)

@app.route('/BuscarEditarUsuario/<string:id>')
def BuscarEditarUsuario_data(id):
        cur=mysql.connection.cursor()
        cur.execute('SELECT * FROM usuarios_cat where Eliminado = 0 and UsuarioId = %s', (id,))
        data = cur.fetchall() 
        return render_template('UsuariosEditar.html',data=data)


@app.route('/updateU/<string:id>', methods=['POST'])
def updateU_data(id):
    NombreEmpleado = request.form['NombreEmpleado']
    Usuario = request.form['Usuario']
    Contraseña = request.form['Contraseña']
    TipoEmpleado = request.form['TipoEmpleado']
    cur = mysql.connection.cursor()
    try:
        cur.execute('UPDATE usuarios_cat SET NombreEmpleado = %s, Usuario = %s, Contraseña = %s, TipoEmpleado = %s WHERE UsuarioId = %s', (NombreEmpleado,Usuario, Contraseña, TipoEmpleado, id))
        mysql.connection.commit()
        flash('Usuario actualizado correctamente', 'success')
    except Exception as e:
        flash('Error al actualizar el usuario: {}'.format(str(e)), 'danger')
    finally:
        cur.close()
    return redirect(url_for('Usuarios_Eliminar'))        

@app.route('/deleteP/<int:orden_id>/<string:nombre_producto>/<int:cantidad>', methods=['GET'])
def delete_producto(orden_id, nombre_producto, cantidad):
    cur = mysql.connection.cursor()
    # Actualizar la cantidad del producto y su total final en Ordenes_det
    cur.execute('''
        UPDATE productos_cat
        SET CantidadStock = CantidadStock + %s
        WHERE NombreProducto = %s
    ''', (cantidad, nombre_producto))
    # Obtener la cantidad, total actual del producto en la orden y el precio

    cur.execute('''
        SELECT OD.Cantidad, OD.TotalFinal, OD.Precio, O.totalOrden, O.Restante
        FROM ordenes_det AS OD
        INNER JOIN ordenes_cat AS O ON O.OrdenId = OD.OrdenId
        INNER JOIN productos_cat AS P ON P.ProductoId = OD.ProductoId
        WHERE O.OrdenId = %s AND P.NombreProducto = %s
    ''', (orden_id, nombre_producto))
    
    producto = cur.fetchone()

    if producto:
        cantidad_actual = producto[0]
        total_final_producto = producto[1]
        precio_producto = producto[2]
        total_orden_actual = producto[3]
        total_restante_actual = producto[4]

        # Si la cantidad a eliminar es menor que la cantidad actual, actualizar cantidad y total final
        if cantidad < cantidad_actual:
            nueva_cantidad = cantidad_actual - cantidad
            nuevo_total_final_producto = total_final_producto - (precio_producto * cantidad)

            # Actualizar la cantidad del producto y su total final en Ordenes_det
            cur.execute('''
                UPDATE ordenes_det
                SET Cantidad = %s, TotalFinal = %s
                WHERE OrdenId = %s AND ProductoId = (
                    SELECT ProductoId FROM productos_cat WHERE NombreProducto = %s LIMIT 1
                )
            ''', (nueva_cantidad, nuevo_total_final_producto, orden_id, nombre_producto))
        
        # Si la cantidad a eliminar es igual o mayor a la cantidad actual, eliminar el producto
        else:
            cur.execute('''
                DELETE FROM ordenes_det
                WHERE OrdenId = %s AND ProductoId = (
                    SELECT ProductoId FROM productos_cat WHERE NombreProducto = %s LIMIT 1
                )
            ''', (orden_id, nombre_producto))

        # Actualizar el total de la orden y el restante restando el precio total del producto eliminado
        nuevo_total_orden = total_orden_actual - (precio_producto * cantidad)
        nuevo_restante_orden = total_restante_actual - (precio_producto * cantidad)

        cur.execute('''
            UPDATE ordenes_cat
            SET totalOrden = %s, Restante = %s
            WHERE OrdenId = %s
        ''', (nuevo_total_orden, nuevo_restante_orden, orden_id))

        # Confirmar los cambios en la base de datos
        mysql.connection.commit()
    
    return redirect(url_for('OrdenesAdmin'))





@app.route('/UsuariosEliminarAdminNom', methods=['POST'])
def Usuarios_Eliminar_Consultar_AdminNom():
    usuario = request.form['NombreEmpleado']
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM usuarios_cat WHERE Eliminado = 0 AND NombreEmpleado LIKE %s', ('%' + usuario + '%',))
    data = cur.fetchall()
    return render_template('UsuariosEliminar.html', data=data)


#estas son las rutas o lo que se pondra en el navegador, de ahi, acceder a lo que se busca
@app.route('/C')
def ClientesAgregarAdmin():
    return render_template('ClientesAgregar.html')

@app.route('/ClientesAgregarAdmin', methods=['POST'])
def Clientes_Agregar_Admin():
    NombreCliente = request.form['NombreCliente']
    Telefono = request.form['Telefono']
    Descuento = request.form['Descuento']

    try:
        cur = mysql.connection.cursor()
        query = '''
            insert into clientes_cat (NombreCliente,Telefono, Descuento, Eliminado)
            values(%s,%s,%s,0);
        '''
        cur.execute(query, (NombreCliente,Telefono, Descuento))
        mysql.connection.commit()
        cur.close()
        
        flash('Cliente agregado correctamente', 'success')
        return redirect(url_for('ClientesAgregarAdmin'))
    except Exception as e:
        print(e)
        flash('Hubo un error al agregar el Cliente', 'danger')
        return redirect(url_for('ClientesAgregarAdmin'))



@app.route('/ClientesEliminar')
def Clientes_Eliminar():
    return render_template('ClientesEliminar.html')

@app.route('/deleteC/<string:id>')
def deleteC_data(id):
        cur=mysql.connection.cursor()
        cur.execute('UPDATE clientes_cat SET Eliminado = 1 WHERE Eliminado = 0 AND ClienteId = %s', (id,))
        mysql.connection.commit()
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM clientes_cat where Eliminado = 0;')
        data = cur.fetchall() 
        return render_template('ClientesEliminar.html',data=data)

@app.route('/BuscarEditarCliente/<string:id>')
def BuscarEditarCliente_data(id):
        cur=mysql.connection.cursor()
        cur.execute('SELECT * FROM clientes_cat where Eliminado = 0 and ClienteId = %s', (id,))
        data = cur.fetchall() 
        return render_template('ClientesEditar.html',data=data)


@app.route('/updateC/<string:id>', methods=['POST'])
def updateC_data(id):
    NombreCliente = request.form['NombreCliente']
    Telefono = request.form['Telefono']
    Descuento = request.form['Descuento']
    cur = mysql.connection.cursor()
    try:
        cur.execute('UPDATE clientes_cat SET NombreCliente= %s, Telefono = %s, Descuento = %s WHERE ClienteId = %s', (NombreCliente,Telefono,Descuento, id))
        mysql.connection.commit()
        flash('Cliente actualizado correctamente', 'success')
    except Exception as e:
        flash('Error al actualizar el Cliente: {}'.format(str(e)), 'danger')
    finally:
        cur.close()
    return redirect(url_for('Clientes_Eliminar'))        


@app.route('/ClientesEliminarAdminNom', methods=['POST'])
def Clientes_Eliminar_Consultar_AdminNom():
    NombreCliente = request.form['NombreCliente']
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM clientes_cat WHERE Eliminado = 0 AND NombreCliente LIKE %s', ('%' + NombreCliente + '%',))
    data = cur.fetchall()
    return render_template('ClientesEliminar.html', data=data)

@app.route('/ClientesDeudaAdminNom', methods=['POST'])
def Clientes_Deuda_Consultar_AdminNom():
    NombreCliente = request.form['NombreCliente']
    cur = mysql.connection.cursor()
    cur.execute('SELECT CD.DeudaId,CD.ClienteId,C.NombreCliente,CD.Deuda,CD.FechaHoraActualizacion,CD.FechaHoraRegistro FROM clientes_credito_det as CD inner join clientes_cat as C on CD.ClienteId = C.ClienteId WHERE CD.StatusPagada = 0 AND C.NombreCliente LIKE %s', ('%' + NombreCliente + '%',))
    data = cur.fetchall()
    return render_template('ClientesDeuda.html', data=data)    

@app.route('/ClientesDeuda')
def Clientes_Deuda():
    return render_template('ClientesDeuda.html')


#estas son las rutas o lo que se pondra en el navegador, de ahi, acceder a lo que se busca
@app.route('/V')
def Venta():
    cur2=mysql.connection.cursor()
    cur = mysql.connection.cursor()
    cur.execute('SELECT NombreCliente, Descuento FROM clientes_cat WHERE Eliminado = 0;')
    data = cur.fetchall()
    cur2.execute('SELECT NombreProducto, Abreviatura, Precio,DisponibleParaDescuento FROM productos_cat WHERE Eliminado = 0;')
    producto=cur2.fetchall()

    return render_template('VentaAdmin.html',producto=producto,data=data)        

@app.route('/OrdenesAgregarAdmin', methods=['POST'])
def Ordenes_Agregar_Admin():
    if 'user_id' in session:
        user_id = session['user_id']

    data = request.get_json()  # Recibir el JSON enviado
    notaVenta = data.get('notaVenta', [])  # Obtener la nota de venta
    formaPago = data.get('formaPago', '')
    totalGeneral = float(data.get('totalGeneral', 0))
    efectivoRecibido_str = data.get('efectivoRecibido', '0')
    TransferenciaTarjetaRecibido_str = data.get('TransferenciaTarjetaRecibido', '0')
    StatusPagada=0
    
# Aseguramos que los valores de efectivoRecibido y TransferenciaTarjetaRecibido sean flotantes o 0 si están vacíos
    efectivoRecibido = float(data.get('efectivoRecibido', 0) or 0)
    TransferenciaTarjetaRecibido = float(data.get('TransferenciaTarjetaRecibido', 0) or 0)
        
    

    if formaPago == "Tarjeta" or formaPago == "Transferencia":
        if totalGeneral == TransferenciaTarjetaRecibido:
            Restante=0
            StatusPagada=1
        else:
            Restante = totalGeneral - TransferenciaTarjetaRecibido
            StatusPagada=0
        try:
            # Insertar en Ordenes_cat
            cur = mysql.connection.cursor()
            query = '''
                INSERT INTO ordenes_cat (UsuarioId, CreditoRapida, StatusPagada, totalOrden, Entregado,EntregadoTransferenciaTarjeta, Restante, FormaDePago, Eliminado)
                VALUES (%s, "Rapida", %s, %s, %s,%s, %s, %s, 0);
            '''
            cur.execute(query, (user_id,StatusPagada, totalGeneral,efectivoRecibido,TransferenciaTarjetaRecibido, Restante, formaPago))
            mysql.connection.commit()

            # Obtener el ID de la orden recién insertada
            cur.execute('SELECT OrdenId FROM ordenes_cat ORDER BY OrdenId DESC LIMIT 1')
            data = cur.fetchone()
            ordenId = data[0]
            cur.close()

            # Insertar en Ordenes_det
            try:
                for item in notaVenta:
                    # Obtener ProductoId basado en el nombre del producto
                    cur2 = mysql.connection.cursor()
                    cur2.execute('SELECT ProductoId FROM productos_cat WHERE NombreProducto = %s', (item['producto'],))
                    data = cur2.fetchone()
                    ProductoId = data[0]
                    cur2.close()                    
                    try:
                        curP = mysql.connection.cursor()
                        curP.execute('UPDATE productos_cat SET CantidadStock= CantidadStock - %s  WHERE ProductoId = %s', (item['cantidad'], ProductoId))
                        mysql.connection.commit()
                    except Exception as e:
                        print(f"Error al actualizar el stock del producto: {e}")
                        flash('Hubo un error al actualizar el stock del producto', 'danger')    

                    # Insertar detalles de la orden
                    sql = '''
                        INSERT INTO ordenes_det (OrdenId, ProductoId, cantidad, precio, TotalFinal)
                        VALUES (%s, %s, %s, %s, %s)
                    '''
                    valores = (ordenId, ProductoId, item['cantidad'], item['precio'], item['total'])
                    cur = mysql.connection.cursor()
                    cur.execute(sql, valores)
                    mysql.connection.commit()
                    cur.close()

                return redirect(url_for('Venta'))

            except Exception as e:
                print(f"Error al insertar detalles de la orden: {e}")
                flash('Hubo un error al agregar los detalles de la orden', 'danger')


        except Exception as e:
            print(f"Error al agregar la orden: {e}")
            flash('Hubo un error al agregar la orden', 'danger')
        
    # Comparar efectivo recibido con el total
    elif efectivoRecibido < totalGeneral:
        Restante = totalGeneral - efectivoRecibido
        try:
            # Insertar en Ordenes_cat
            cur = mysql.connection.cursor()
            query = '''
                INSERT INTO ordenes_cat (UsuarioId, CreditoRapida, StatusPagada, totalOrden, Entregado,EntregadoTransferenciaTarjeta, Restante, FormaDePago, Eliminado)
                VALUES (%s, "Rapida", 0, %s, %s,%s,%s, %s, 0);
            '''
            cur.execute(query, (user_id, totalGeneral, efectivoRecibido,TransferenciaTarjetaRecibido, Restante, formaPago))
            mysql.connection.commit()

            # Obtener el ID de la orden recién insertada
            cur.execute('SELECT OrdenId FROM ordenes_cat ORDER BY OrdenId DESC LIMIT 1')
            data = cur.fetchone()
            ordenId = data[0]
            cur.close()

            # Insertar en Ordenes_det
            try:
                for item in notaVenta:
                    # Obtener ProductoId basado en el nombre del producto
                    cur2 = mysql.connection.cursor()
                    cur2.execute('SELECT ProductoId FROM productos_cat WHERE NombreProducto = %s', (item['producto'],))
                    data = cur2.fetchone()
                    ProductoId = data[0]
                    cur2.close()                    
                    try:
                        curP = mysql.connection.cursor()
                        curP.execute('UPDATE productos_cat SET CantidadStock= CantidadStock - %s  WHERE ProductoId = %s', (item['cantidad'], ProductoId))
                        mysql.connection.commit()
                    except Exception as e:
                        print(f"Error al actualizar el stock del producto: {e}")
                        flash('Hubo un error al actualizar el stock del producto', 'danger')    

                    # Insertar detalles de la orden
                    sql = '''
                        INSERT INTO ordenes_det (OrdenId, ProductoId, cantidad, precio, TotalFinal)
                        VALUES (%s, %s, %s, %s, %s)
                    '''
                    valores = (ordenId, ProductoId, item['cantidad'], item['precio'], item['total'])
                    cur = mysql.connection.cursor()
                    cur.execute(sql, valores)
                    mysql.connection.commit()
                    cur.close()

                return redirect(url_for('Venta'))

            except Exception as e:
                print(f"Error al insertar detalles de la orden: {e}")
                flash('Hubo un error al agregar los detalles de la orden', 'danger')


        except Exception as e:
            print(f"Error al agregar la orden: {e}")
            flash('Hubo un error al agregar la orden', 'danger')
    
    # Si el efectivo recibido fue mayor o igual que el total
    else:
        Restante = 0
        try:
            # Insertar en Ordenes_cat
            cur = mysql.connection.cursor()
            query = '''
                INSERT INTO ordenes_cat (UsuarioId, CreditoRapida, StatusPagada, totalOrden, Entregado,EntregadoTransferenciaTarjeta, Restante, FormaDePago, Eliminado)
                VALUES (%s, "Rapida", 1, %s, %s, %s,%s, %s, 0);
            '''
            cur.execute(query, (user_id, totalGeneral, efectivoRecibido,TransferenciaTarjetaRecibido, Restante, formaPago))
            mysql.connection.commit()

            # Obtener el ID de la orden recién insertada
            cur.execute('SELECT OrdenId FROM ordenes_cat ORDER BY OrdenId DESC LIMIT 1')
            data = cur.fetchone()
            ordenId = data[0]
            cur.close()

            # Insertar en Ordenes_det
            try:
                for item in notaVenta:
                    # Obtener ProductoId basado en el nombre del producto
                    cur2 = mysql.connection.cursor()
                    cur2.execute('SELECT ProductoId FROM productos_cat WHERE NombreProducto = %s', (item['producto'],))
                    data = cur2.fetchone()
                    ProductoId = data[0]
                    cur2.close()                    
                    try:
                        curP = mysql.connection.cursor()
                        curP.execute('UPDATE productos_cat SET CantidadStock= CantidadStock - %s  WHERE ProductoId = %s', (item['cantidad'], ProductoId))
                        mysql.connection.commit()
                    except Exception as e:
                        print(f"Error al actualizar el stock del producto: {e}")
                        flash('Hubo un error al actualizar el stock del producto', 'danger')    

                    # Insertar detalles de la orden
                    sql = '''
                        INSERT INTO ordenes_det (OrdenId, ProductoId, cantidad, precio, TotalFinal)
                        VALUES (%s, %s, %s, %s, %s)
                    '''
                    valores = (ordenId, ProductoId, item['cantidad'], item['precio'], item['total'])
                    cur = mysql.connection.cursor()
                    cur.execute(sql, valores)
                    mysql.connection.commit()
                    cur.close()

                return redirect(url_for('Venta'))

            except Exception as e:
                print(f"Error al insertar detalles de la orden: {e}")
                flash('Hubo un error al agregar los detalles de la orden', 'danger')


        except Exception as e:
            print(f"Error al agregar la orden: {e}")
            flash('Hubo un error al agregar la orden', 'danger')

    return redirect(url_for('Venta'))    

@app.route('/OrdenesCreditoAgregarAdmin', methods=['POST'])
def Ordenes_Credito_Agregar_Admin():
    if 'user_id' in session:
        user_id = session['user_id']

    data = request.get_json()  # Recibir el JSON enviado
    notaVenta = data.get('notaVenta', [])  # Obtener la nota de venta
    formaPago = data.get('formaPago', '')
    totalGeneral = float(data.get('totalGeneral', 0))
    efectivoRecibido_str = data.get('efectivoRecibido', '0')
    Cliente = data.get('Cliente', '')
    TransferenciaTarjetaRecibido_str = data.get('TransferenciaTarjetaRecibido', '0')

# Aseguramos que los valores de efectivoRecibido y TransferenciaTarjetaRecibido sean flotantes o 0 si están vacíos
    efectivoRecibido = float(data.get('efectivoRecibido', 0) or 0)
    TransferenciaTarjetaRecibido = float(data.get('TransferenciaTarjetaRecibido', 0) or 0)
    
   
    # Obtener el ID del cliente recién
    cur = mysql.connection.cursor()
    cur.execute('SELECT ClienteId FROM clientes_cat WHERE NombreCliente = %s', (Cliente,))
    dataC = cur.fetchone()
    ClienteId = dataC[0]
    cur.close()

    # Obtener el OrdenID del cliente si sigue comprando (actualizar orden)
    cur = mysql.connection.cursor()
    cur.execute('SELECT OrdenId FROM ordenes_cat WHERE ClienteId = %s and statusPagada=0', (ClienteId,))
    dataO = cur.fetchone()
    cur.close()

    # Verificar si se encontró una orden existente
    if dataO is not None:
        OrIdExistente = dataO[0]
        print(OrIdExistente)
        try:
            cur = mysql.connection.cursor()
            cur.execute('UPDATE ordenes_cat SET totalOrden= totalOrden + %s, Restante = Restante + %s WHERE OrdenId = %s', (totalGeneral, totalGeneral, OrIdExistente))
            mysql.connection.commit()

            # Insertar en Ordenes_det
            try:
                for item in notaVenta:
                    # Obtener ProductoId basado en el nombre del producto
                    cur2 = mysql.connection.cursor()
                    cur2.execute('SELECT ProductoId FROM productos_cat WHERE NombreProducto = %s', (item['producto'],))
                    data = cur2.fetchone()
                    ProductoId = data[0]
                    cur2.close()
                    try:
                        curP = mysql.connection.cursor()
                        curP.execute('UPDATE productos_cat SET CantidadStock= CantidadStock - %s  WHERE ProductoId = %s', (item['cantidad'], ProductoId))
                        mysql.connection.commit()
                    except Exception as e:
                        print(f"Error al actualizar el stock del producto: {e}")
                        flash('Hubo un error al actualizar el stock del producto', 'danger')    

                    # Insertar detalles de la orden
                    sql = '''
                        INSERT INTO ordenes_det (OrdenId, ProductoId, cantidad, precio, TotalFinal)
                        VALUES (%s, %s, %s, %s, %s)
                    '''
                    valores = (OrIdExistente, ProductoId, item['cantidad'], item['precio'], item['total'])
                    cur = mysql.connection.cursor()
                    cur.execute(sql, valores)
                    mysql.connection.commit()
                    cur.close()

                return redirect(url_for('Venta'))

            except Exception as e:
                print(f"Error al insertar detalles de la orden: {e}")
                flash('Hubo un error al agregar los detalles de la orden', 'danger')

        except Exception as e:
            print(f"Error al actualizar la orden existente: {e}")
            flash('Hubo un error al actualizar la orden existente', 'danger')

    else:
        # Verificar si la cadena está vacía o no es numérica antes de convertirla
        if efectivoRecibido_str and efectivoRecibido_str.strip().replace('.', '', 1).isdigit():
            efectivoRecibido = float(efectivoRecibido_str)
        else:
            efectivoRecibido = 0.0

        # Verificar si la cadena está vacía o no es numérica antes de convertirla
        if TransferenciaTarjetaRecibido_str and TransferenciaTarjetaRecibido_str.strip().replace('.', '', 1).isdigit():
            TransferenciaTarjetaRecibido = float(TransferenciaTarjetaRecibido_str)
        else:
            TransferenciaTarjetaRecibido = 0.0        
    
        try:
            # Insertar en Ordenes_cat
            cur = mysql.connection.cursor()
            query = '''
                INSERT INTO ordenes_cat (UsuarioId, ClienteId, CreditoRapida, StatusPagada, totalOrden, Entregado,EntregadoTransferenciaTarjeta, Restante, Eliminado)
                VALUES (%s,%s, "Credito", 0, %s, %s,%s, %s, 0);
            '''
            cur.execute(query, (user_id, ClienteId, totalGeneral, efectivoRecibido,TransferenciaTarjetaRecibido, totalGeneral))
            mysql.connection.commit()

            # Obtener el ID de la orden recién insertada
            cur.execute('SELECT OrdenId FROM ordenes_cat ORDER BY OrdenId DESC LIMIT 1')
            data = cur.fetchone()
            ordenId = data[0]
            cur.close()

            # Insertar en Ordenes_det
            try:
                for item in notaVenta:
                    # Obtener ProductoId basado en el nombre del producto
                    cur2 = mysql.connection.cursor()
                    cur2.execute('SELECT ProductoId FROM productos_cat WHERE NombreProducto = %s', (item['producto'],))
                    data = cur2.fetchone()
                    ProductoId = data[0]
                    cur2.close()                   
                    try:
                        curP = mysql.connection.cursor()
                        curP.execute('UPDATE productos_cat SET CantidadStock= CantidadStock - %s  WHERE ProductoId = %s', (item['cantidad'], ProductoId))
                        mysql.connection.commit()
                    except Exception as e:
                        print(f"Error al actualizar el stock del producto: {e}")
                        flash('Hubo un error al actualizar el stock del producto', 'danger')    
                        
                    # Insertar detalles de la orden
                    sql = '''
                        INSERT INTO ordenes_det (OrdenId, ProductoId, cantidad, precio, TotalFinal)
                        VALUES (%s, %s, %s, %s, %s)
                    '''
                    valores = (ordenId, ProductoId, item['cantidad'], item['precio'], item['total'])
                    cur = mysql.connection.cursor()
                    cur.execute(sql, valores)
                    mysql.connection.commit()
                    cur.close()

                return redirect(url_for('Venta'))

            except Exception as e:
                print(f"Error al insertar detalles de la orden: {e}")
                flash('Hubo un error al agregar los detalles de la orden', 'danger')

        except Exception as e:
            print(f"Error al agregar la orden: {e}")
            flash('Hubo un error al agregar la orden', 'danger')
        
    return redirect(url_for('Venta'))
   

@app.route('/verificar_contraseña', methods=['POST'])
def verificar_contraseña():
    codigo_ingresado = request.json['codigo']
    
    cur = mysql.connection.cursor()


    # Consulta para verificar la contraseña
    query = '''
        SELECT * FROM usuarios_cat 
        WHERE Contraseña = %s 
        AND (TipoEmpleado = 'Administrador' OR TipoEmpleado = 'Supervisor') 
        AND Eliminado = 0
    '''
    cur.execute(query, (codigo_ingresado,))
    usuario = cur.fetchone()
    
    cur.close()

    if usuario:
        return jsonify({"valid": True}), 200
    else:
        return jsonify({"valid": False}), 403

@app.route('/procesarCobro', methods=['POST'])
def procesar_cobro():
    data = request.get_json()
    orden_id = data.get('ordenId')
    total_a_pagar = data.get('totalAPagar')
    forma_pago = data.get('formaPago')
    efectivo_recibido = data.get('efectivoRecibido')
    transferencia_tarjeta_recibido = data.get('transferenciaTarjetaRecibido')
    cambio = data.get('cambio')

    try:
        cur = mysql.connection.cursor()
        cur.execute('UPDATE ordenes_cat SET Restante = 0.00,StatusPagada=1, Entregado=Entregado + %s,EntregadoTransferenciaTarjeta=EntregadoTransferenciaTarjeta + %s WHERE OrdenId = %s', (efectivo_recibido, transferencia_tarjeta_recibido, orden_id))
        mysql.connection.commit()
# Devolver un JSON con un mensaje de éxito
        return jsonify({"success": True, "message": "Cobro realizado con éxito"})
        
    except Exception as e:
        print(f"Error al cobrar la orden: {e}")
        return jsonify({"success": False, "message": "Error al procesar el cobro"})
    


    return redirect(url_for('OrdenesAdmin'))        



@app.route('/procesarCobroC', methods=['POST'])
def procesar_cobroC():
    data = request.get_json()
    orden_id = data.get('ordenId')
    total_a_pagar = data.get('totalAPagar')
    forma_pago = data.get('formaPago')
    efectivo_recibido = data.get('efectivoRecibido')
    transferencia_tarjeta_recibido = data.get('transferenciaTarjetaRecibido')
    cambio = data.get('cambio')

    try:
        cur = mysql.connection.cursor()
        cur.execute('UPDATE ordenes_cat SET Restante = 0.00,StatusPagada=1, Entregado=Entregado + %s,EntregadoTransferenciaTarjeta=EntregadoTransferenciaTarjeta + %s WHERE OrdenId = %s', (efectivo_recibido, transferencia_tarjeta_recibido, orden_id))
        mysql.connection.commit()
# Devolver un JSON con un mensaje de éxito
        return jsonify({"success": True, "message": "Cobro realizado con éxito"})
        
    except Exception as e:
        print(f"Error al cobrar la orden: {e}")
        return jsonify({"success": False, "message": "Error al procesar el cobro"})
    


    return redirect(url_for('OrdenesAdminClientes'))        

@app.route('/procesarCobroDeuda', methods=['POST'])
def procesar_cobro_Deuda():
    data = request.get_json()
    orden_id = data.get('ordenId')
    total_a_pagar = float(data.get('totalAPagar', 0))
    forma_pago = data.get('formaPago')
    efectivo_recibido = float(data.get('efectivoRecibido', 0))
    transferencia_tarjeta_recibido = float(data.get('transferenciaTarjetaRecibido', 0))
    cambio = float(data.get('cambio', 0))
    suma = efectivo_recibido + transferencia_tarjeta_recibido

    print(f"Orden ID: {orden_id}")
    print(f"Total a pagar: {total_a_pagar}")
    print(f"Efectivo recibido: {efectivo_recibido}")
    print(f"Transferencia/Tarjeta recibida: {transferencia_tarjeta_recibido}")
    
    try:
        cur = mysql.connection.cursor()
        
        if total_a_pagar <= suma:
            # Si el total a pagar es menor o igual a la suma, marcamos la deuda como pagada
            cur.execute(
                'UPDATE clientes_credito_det SET StatusPagada = 1, Entregado = Entregado + %s, EntregadoTransferenciaTarjeta = EntregadoTransferenciaTarjeta + %s WHERE DeudaId = %s',
                (efectivo_recibido, transferencia_tarjeta_recibido, orden_id)
            )
            message = "Cobro realizado con éxito, deuda pagada por completo."
        
        else:
            # Si el pago no cubre el total, actualizamos la deuda restante y el pago parcial
            deuda_restante = total_a_pagar - suma
            cur.execute(
                'UPDATE clientes_credito_det SET StatusPagada = 0, Deuda = Deuda - %s, Entregado = Entregado + %s, EntregadoTransferenciaTarjeta = EntregadoTransferenciaTarjeta + %s WHERE DeudaId = %s',
                (suma, efectivo_recibido, transferencia_tarjeta_recibido, orden_id)
            )
            message = "Cobro realizado con éxito, pero aún queda deuda pendiente."

        mysql.connection.commit()
        return jsonify({"success": True, "message": message})

    except Exception as e:
        print(f"Error al cobrar la orden: {e}")
        return jsonify({"success": False, "message": "Error al procesar el cobro"})
   


@app.route('/obtenerDetallesOrden/<int:orden_id>', methods=['GET'])
def obtener_detalles_orden(orden_id):
    print(orden_id)
    cur = mysql.connection.cursor()
    query = """
    SELECT P.NombreProducto, COALESCE(OD.Precio, 0), OD.Cantidad, COALESCE(OD.TotalFinal, 0), O.totalOrden,C.NombreCliente
    FROM ordenes_cat AS O 
    INNER JOIN ordenes_det AS OD ON O.OrdenId = OD.OrdenId
    INNER JOIN clientes_cat AS C ON O.ClienteId = C.ClienteId 
    INNER JOIN productos_cat AS P ON P.ProductoId = OD.ProductoId 
    WHERE O.OrdenId = %s 
    ORDER BY O.OrdenId;
    """

    cur.execute(query, (orden_id,))
    detalles = cur.fetchall()
    print (detalles)
    # Obtener el total de la orden, asegurando que siempre sea un número
    if detalles:
        total_orden = detalles[0][4]  # El campo totalOrden de la primera fila
        cliente = detalles[0][5]  # El campo Cliente de la primera fila

        if total_orden is None:
            total_orden = 0  # Si totalOrden es None, asignamos 0
    else:
        total_orden = 0  # Si no hay detalles, total_orden es 0

    productos = [{'nombre': row[0], 'precio': float(row[1]), 'cantidad': row[2], 'total_final': float(row[3])} for row in detalles]

    return jsonify({'productos': productos, 'totalOrden': float(total_orden),'cliente': cliente})  # Aseguramos que totalOrden sea un flotante


@app.route('/obtenerDetallesDeuda/<int:orden_id>', methods=['GET'])
def obtener_detalles_deuda(orden_id):
    cur = mysql.connection.cursor()
    query = """
    SELECT Deuda
    FROM clientes_credito_det  -- Especifica la tabla correcta
    WHERE ClienteId = %s 
    """

    cur.execute(query, (orden_id,))  # Usamos `orden_id` que coincide con la ruta
    detalles = cur.fetchone()
    
    # Obtener el total de la orden, asegurando que siempre sea un número
    if detalles:
        total_orden = detalles[0]  # El campo totalOrden de la primera fila

        if total_orden is None:
            total_orden = 0  # Si totalOrden es None, asignamos 0
    else:
        total_orden = 0  # Si no hay detalles, total_orden es 0

    return jsonify({'totalOrden': float(total_orden)})  # Aseguramos que totalOrden sea un flotante

@app.route('/ActualizarCredito', methods=['POST'])
def actualizar_credito():
    data = request.get_json()  # Obtener el JSON de la solicitud
    orden_id = data.get('ordenId')
    restante = data.get('restante')
    cur = mysql.connection.cursor()
    cur.execute('SELECT ClienteId FROM ordenes_cat WHERE OrdenId = %s', (orden_id,))
    cliente_id = cur.fetchone()

    try:
        print("aver")
        # Consultar la deuda actual del cliente
        cur.execute('SELECT StatusPagada FROM clientes_credito_det WHERE ClienteId = %s ORDER BY FechaHoraRegistro DESC LIMIT 1', (cliente_id,))
        deuda = cur.fetchone()
        print(deuda[0])
        if deuda[0]==0:
            print("si")
            # Actualizar la deuda si ya existe un registro
            cur.execute('UPDATE clientes_credito_det SET Deuda = Deuda + %s WHERE ClienteId = %s', (restante, cliente_id))
            cur.execute('UPDATE ordenes_cat SET StatusPagada = 1 WHERE OrdenId = %s', (orden_id,))
        else:
            # Insertar un nuevo registro si no existe deuda previa
            print("no")
            cur.execute('INSERT INTO clientes_credito_det (ClienteId, Deuda,Entregado,EntregadoTransferenciaTarjeta,StatusPagada) VALUES (%s, %s,0,0,0)', (cliente_id, restante))
            cur.execute('UPDATE ordenes_cat SET StatusPagada = 1 WHERE OrdenId = %s', (orden_id,))

        
        mysql.connection.commit()
        return jsonify({"success": True, "message": "Crédito realizado con éxito"})
    
    except Exception as e:
        print(f"Error al actualizar crédito: {e}")
        return jsonify({"success": False, "message": "Error al procesar el crédito"})
    
    finally:
        cur.close()
    

@app.route('/IngresosAdmin')
def Ingresos_Admin():
    return render_template('IngresosAdmin.html')



@app.route('/Ingresos', methods=['POST'])
def Ingresos():
    cur = mysql.connection.cursor()
    fechainicio = request.form.get('FechaInicio')
    fechafinal = request.form.get('FechaFinal')

    if fechainicio > fechafinal:
        fechainicio, fechafinal = fechafinal, fechainicio

    # Consulta para obtener la suma de Entregado y EntregadoTransferenciaTarjeta
    entregado_query = '''
        SELECT 
            (SELECT COALESCE(SUM(Entregado), 0) FROM ordenes_cat WHERE StatusPagada = 1 {}) +
            (SELECT COALESCE(SUM(Entregado), 0) FROM clientes_credito_det WHERE StatusPagada = 1 {}) AS TotalEntregado
    '''
    transfer_query = '''
        SELECT 
            (SELECT COALESCE(SUM(EntregadoTransferenciaTarjeta), 0) FROM ordenes_cat WHERE StatusPagada = 1 {}) +
            (SELECT COALESCE(SUM(EntregadoTransferenciaTarjeta), 0) FROM clientes_credito_det WHERE StatusPagada = 1 {}) AS TotalTransfer
    '''

    conditions = []
    params = []

    if fechainicio and not fechafinal:
        conditions.append("AND DATE(FechaHoraRegistro) >= %s")
        params.append(fechainicio)
    elif not fechainicio and fechafinal:
        conditions.append("AND DATE(FechaHoraRegistro) <= %s")
        params.append(fechafinal)
    elif fechainicio and fechafinal:
        conditions.append("AND DATE(FechaHoraRegistro) BETWEEN %s AND %s")
        params.extend([fechainicio, fechafinal])

    condition_str = " ".join(conditions)

    # Ejecutar la consulta para la suma de Entregado
    cur.execute(entregado_query.format(condition_str, condition_str), tuple(params * 2))
    result_entregado = cur.fetchone()
    total_entregado = result_entregado[0] if result_entregado else 0.0

    # Ejecutar la consulta para la suma de EntregadoTransferenciaTarjeta
    cur.execute(transfer_query.format(condition_str, condition_str), tuple(params * 2))
    result_transfer = cur.fetchone()
    total_transfer = result_transfer[0] if result_transfer else 0.0

    cur.close()
    return render_template('IngresosAdmin.html', total_entregado=total_entregado, total_transfer=total_transfer)




if __name__ == '__main__':
    app.run(debug=True)
