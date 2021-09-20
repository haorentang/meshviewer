# coding=utf-8
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QTimer
from PyQt5.QtOpenGL import QGLWidget
import sys
import os
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *

current_path = None


def loadobjpath(paths):
    print("load called")

    with open(paths) as file:
        lines = file.readlines()
        vStrings = [x.strip('v') for x in lines if x.startswith('v ')]
        vertices = convertVertices(vStrings)
        if np.amax(vertices) <= 1.2:
            vertices /= np.amax(vertices)
        else:
            vertices /= np.amax(vertices) / 2
        vnStrings = [x.strip('vn') for x in lines if x.startswith('vn')]
        if not vnStrings:
            normals = fillNormalsArray(len(vStrings), vertices)
        else:
            normals = convertVertices(vnStrings)
        faces = [x.strip('f') for x in lines if x.startswith('f')]

    gVertexArraySeparate = createVertexArraySeparate(faces, normals, vertices)
    edges = getedges(vertices, faces)

    return gVertexArraySeparate, edges


def getedges(vertices, faces):
    edges = np.zeros((len(faces) * 3, 2, 3))
    edgei = np.zeros((len(faces) * 3, 2))
    ei = 0
    for face in faces:
        fvertices = face.split()
        edgei[ei][0] = fvertices[0]
        edgei[ei][1] = fvertices[1]
        edgei[ei + 1][0] = fvertices[0]
        edgei[ei + 1][1] = fvertices[2]
        edgei[ei + 2][0] = fvertices[1]
        edgei[ei + 2][1] = fvertices[2]
        ei += 3
    for i in range(len(faces) * 3):
        edges[i][0] = vertices[int(edgei[i][0]) - 1]
        edges[i][1] = vertices[int(edgei[i][1]) - 1]
    return edges


def fillNormalsArray(numberOfVertices, vertices):
    normals = np.zeros((numberOfVertices, 3))
    i = 0
    for vertice in vertices:
        normals[i] = (1 / np.sqrt(np.dot(vertice, vertice))) * np.array(vertice)
        i += 1
    return normals


def convertVertices(verticesStrings):
    v = np.zeros((len(verticesStrings), 3))
    i = 0
    for vertice in verticesStrings:
        j = 0
        for t in vertice.split():
            try:
                v[i][j] = (float(t))
            except ValueError:
                pass
            j += 1
        i += 1
    return v


def createVertexArraySeparate(faces, normals, vertices):
    varr = np.zeros((len(faces) * 6, 3), 'float32')
    i = 0
    for face in faces:
        for f in face.split():
            if '//' in f:
                verticeIndex = int(f.split('//')[0]) - 1
                normalsIndex = int(f.split('//')[1]) - 1
            elif '/' in f:
                if len(f.split('/')) == 2:
                    verticeIndex = int(f.split('/')[0]) - 1
                    normalsIndex = int(f.split('/')[0]) - 1
                else:
                    verticeIndex = int(f.split('/')[0]) - 1
                    normalsIndex = int(f.split('/')[2]) - 1
            else:
                verticeIndex = int(f.split()[0]) - 1
                normalsIndex = int(f.split()[0]) - 1
            varr[i] = normals[normalsIndex]
            varr[i + 1] = vertices[verticeIndex]
            i += 2
    return varr



class MainWindow(QMainWindow):

    def __init__(self, parent=None):

        super(MainWindow, self).__init__(parent)

        self.setAcceptDrops(True)

        self.basic()

    def basic(self):
        global gVertexArraySeparate

        self.setWindowTitle("MyGUI")
        self.resize(1500, 1000)

        screen = QDesktopWidget().geometry()
        self_size = self.geometry()
        self.move(int((screen.width() - self_size.width()) / 2), int((screen.height() - self_size.height()) / 2))

        self.layout = self.layout = QGridLayout(self)

        self.set_file_bar()
        self.set_view_bar()

        self.glwidget = GLWidget(self)
        self.layout.addWidget(self.glwidget)
        self.glwidget.setGeometry(200, 100, 1200, 800)

    def set_file_bar(self):
        self.menubar = self.menuBar()
        self.file = self.menubar.addMenu("file")
        self.layout.addWidget(self.menubar)

        openbutton = QAction("Open", self)
        self.file.addAction(openbutton)
        openbutton.triggered.connect(self.openfile)

        closebutton = QAction("Close", self)
        self.file.addAction(closebutton)
        closebutton.triggered.connect(self.close)

    def set_view_bar(self):
        self.viewbar = self.menuBar()
        self.view = self.menubar.addMenu("view")
        self.layout.addWidget(self.viewbar)

        edgebutton = QAction("edgeview", self)
        self.view.addAction(edgebutton)
        edgebutton.triggered.connect(self.edgeview)

    def edgeview(self):
        if self.glwidget.view == "faces":
            self.glwidget.view = "edges"
        elif self.glwidget.view == "edges":
            self.glwidget.view = "faces"

    def openfile(self):
        global current_path
        download_path, filetype = QFileDialog.getOpenFileName(self, "browse", ".")
        print(download_path)
        current_path = download_path
        self.placegl()

    def dragEnterEvent(self, e):
        if e.mimeData().text().endswith('.obj'):
            e.accept()
        else:
            QMessageBox.warning(self, "Warning", "file format should be obj", QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.Yes)
            e.ignore()

    def dropEvent(self, e):
        global current_path
        path = e.mimeData().text().replace('file:///', '')
        current_path = path
        self.placegl()

    def placegl(self):
        global current_path
        VASeparate, edges = loadobjpath(current_path)
        self.glwidget.setvaseperate(VASeparate)
        self.glwidget.edges = edges


class GLWidget(QGLWidget):

    def __init__(self, parent):
        print("initialized")
        QGLWidget.__init__(self, parent)

        self.VASeparate = None
        self.edges = None
        self.isload = False
        self.view = "faces"

        self.theta = 0.
        self.fi = 0

        self.shiftx = 0
        self.shifty = 0
        self.shiftz = 0

        self._mousePosition = None

        self.modeFlag = 0
        self.distanceFromOrigin = 30
        self.setFocusPolicy(Qt.StrongFocus)

        self.setMouseTracking(False)

        timer = QTimer(self)
        timer.timeout.connect(self.updateGL)
        timer.start(20)

    def initializeGL(self):
        print("initialized called")
        glClearColor(0.0, 0.0, 0.0, 0)
        return

    def setvaseperate(self, VASeparate):
        self.isload = True
        self.VASeparate = VASeparate

    def paintGL(self):

        def draw_glDrawArray(varr):
            glEnableClientState(GL_VERTEX_ARRAY)
            glEnableClientState(GL_NORMAL_ARRAY)
            glNormalPointer(GL_FLOAT, 6 * varr.itemsize, varr)
            glVertexPointer(3, GL_FLOAT, 6 * varr.itemsize, ctypes.c_void_p(varr.ctypes.data + 3 * varr.itemsize))
            glDrawArrays(GL_TRIANGLES, 0, int(varr.size / 6))

        def drawEdges(edges):
            glBegin(GL_LINES)
            for i in range(len(edges)):
                glColor3ub(255, 0, 0)
                glVertex3fv(edges[i][0])
                glVertex3fv(edges[i][1])
            glEnd()

        def drawFrame():
            glBegin(GL_LINES)
            glColor3ub(255, 0, 0)
            glVertex3fv(np.array([0., 0., 0.]))
            glVertex3fv(np.array([10., 0., 0.]))
            glColor3ub(0, 255, 0)
            glVertex3fv(np.array([0., 0., 0.]))
            glVertex3fv(np.array([0., 10., 0.]))
            glColor3ub(0, 0, 255)
            glVertex3fv(np.array([0., 0., 0]))
            glVertex3fv(np.array([0., 0., 10.]))
            glEnd()

        def lighting():
            glEnable(GL_LIGHTING)
            glEnable(GL_LIGHT0)
            glEnable(GL_LIGHT1)
            glEnable(GL_LIGHT2)
            glEnable(GL_LIGHT3)
            glEnable(GL_LIGHT4)
            glEnable(GL_LIGHT5)
            glPushMatrix()

            lightPos0 = (0, 0, 10, 0)
            lightPos1 = (0, 10, 0, 0)
            lightPos2 = (10, 0, 0, 0)
            lightPos3 = (0, 0, -10, 0)
            lightPos4 = (0, -10, 0, 0)
            lightPos5 = (-10, 0, 0, 0)

            glLightfv(GL_LIGHT0, GL_POSITION, lightPos0)
            glLightfv(GL_LIGHT1, GL_POSITION, lightPos1)
            glLightfv(GL_LIGHT2, GL_POSITION, lightPos2)
            glLightfv(GL_LIGHT3, GL_POSITION, lightPos3)
            glLightfv(GL_LIGHT4, GL_POSITION, lightPos4)
            glLightfv(GL_LIGHT5, GL_POSITION, lightPos5)

            glPopMatrix()

            LightColor0 = (.1, .1, .1, 1.)
            LightColor1 = (.1, .1, .1, 1.)
            LightColor2 = (.1, .1, .1, 1.)
            LightColor3 = (.1, .1, .1, 1.)
            LightColor4 = (.1, .1, .1, 1.)
            LightColor5 = (.1, .1, .1, 1.)

            glLightfv(GL_LIGHT0, GL_AMBIENT, LightColor0)
            glLightfv(GL_LIGHT1, GL_AMBIENT, LightColor1)
            glLightfv(GL_LIGHT2, GL_AMBIENT, LightColor2)
            glLightfv(GL_LIGHT3, GL_AMBIENT, LightColor3)
            glLightfv(GL_LIGHT4, GL_AMBIENT, LightColor4)
            glLightfv(GL_LIGHT5, GL_AMBIENT, LightColor5)


            diffuseObjectColor = (0.5, 0.6, 0.3, 1.)

            glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, diffuseObjectColor)

            glEnable(GL_LIGHTING)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.distanceFromOrigin, 1, 1, 10)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(5 * np.cos(self.fi) * np.cos(self.theta), 5 * np.cos(self.fi) * np.sin(self.theta),
                  5 * np.sin(self.fi),
                  self.shiftx, self.shifty, self.shiftz,
                  - np.sin(self.fi) * np.cos(self.theta), - np.sin(self.fi) * np.sin(self.theta), np.cos(self.fi))

        drawFrame()
        lighting()

        glPushMatrix()
        if self.isload:
            if self.view == "faces":
                draw_glDrawArray(self.VASeparate)
            elif self.view == "edges":
                drawEdges(self.edges)
        glPopMatrix()

        glDisable(GL_LIGHTING)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_A:
            self.theta += np.radians(-10 % 360)
        elif event.key() == Qt.Key_D:
            self.theta += np.radians(10 % 360)
        elif event.key() == Qt.Key_W:
            if self.fi < 90:
                self.fi += np.radians(-10 % 360)
        elif event.key() == Qt.Key_S:
            if self.fi > -90:
                self.fi -= np.radians(-10 % 360)
        elif event.key() == Qt.Key_Up:
            self.shiftz += 0.1 * np.cos(self.fi)
            self.shiftx -= 0.1 * np.sin(self.fi) * np.cos(self.theta)
            self.shifty -= 0.1 * np.sin(self.fi) * np.sin(self.theta)
        elif event.key() == Qt.Key_Down:
            self.shiftz -= 0.1 * np.cos(self.fi)
            self.shiftx += 0.1 * np.sin(self.fi) * np.cos(self.theta)
            self.shifty += 0.1 * np.sin(self.fi) * np.sin(self.theta)
        elif event.key() == Qt.Key_Left:
            self.shiftx += 0.1 * np.sin(self.theta)
            self.shifty -= 0.1 * np.cos(self.theta)
        elif event.key() == Qt.Key_Right:
            self.shiftx -= 0.1 * np.sin(self.theta)
            self.shifty += 0.1 * np.cos(self.theta)
        elif event.key() == Qt.Key_Escape:
            self.close()
        pass

    def wheelEvent(self, event):
        if int(event.angleDelta().y()) < 0:
            self.distanceFromOrigin += 1
        elif int(event.angleDelta().y()) > 0:
            self.distanceFromOrigin -= 1

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setMouseTracking(True)
            self._mousePosition = event.pos()

    def mouseMoveEvent(self, event):
        dx = event.x() - self._mousePosition.x()
        dy = -(event.y() - self._mousePosition.y())
        adjustx = 1
        adjusty = 1

        if event.x() < 690 or event.x() > 730:
            adjustx = event.x() - 710
        if event.y() < 430 or event.y() > 470:
            adjusty = event.y() - 450

        self._mousePosition = event.pos()
        self.theta += np.radians(-dx % (360 * adjustx))
        self.fi += np.radians(-dy % (360 * adjusty))

    def mouseReleaseEvent(self, event):
        self.setMouseTracking(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
