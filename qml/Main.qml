pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root
    width: 1200
    height: 675
    minimumWidth: 960
    minimumHeight: 540
    visible: true
    color: "#070824"
    title: "Millonario educativo · V2"

    property color navy: "#071a63"
    property color royal: "#26278b"
    property color silver: "#d7d8e0"
    property color gold: "#f5b82e"
    property bool menuVisible: true
    property bool loadingEditor: false
    property bool editorDirty: false
    property bool importSucceeded: false
    property url pendingExcelFile: ""
    property var pendingEditorAction: null

    component TopButton: Button {
        id: topButton
        implicitHeight: 38
        leftPadding: 18
        rightPadding: 18
        contentItem: Label {
            text: topButton.text
            color: "white"
            font.bold: true
            font.pixelSize: 14
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: height / 2
            color: topButton.down ? "#3f419d" : "#c5121b59"
            border.color: topButton.hovered ? root.gold : root.silver
            border.width: 2
        }
    }

    component EditorField: TextField {
        id: editorField
        color: "white"
        placeholderTextColor: "#9299be"
        selectionColor: root.royal
        selectedTextColor: "white"
        font.pixelSize: 15
        leftPadding: 12
        rightPadding: 12
        background: Rectangle {
            radius: 7
            color: editorField.activeFocus ? "#222958" : "#171c44"
            border.color: editorField.activeFocus ? root.gold : "#737aa8"
            border.width: editorField.activeFocus ? 2 : 1
        }
    }

    component MenuButton: Button {
        id: menuButton
        implicitWidth: Math.min(root.width * 0.52, 620)
        implicitHeight: Math.max(68, root.height * 0.105)
        hoverEnabled: true
        contentItem: Label {
            text: menuButton.text
            color: "white"
            font.bold: true
            font.pixelSize: Math.max(22, root.height * 0.038)
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: height / 2
            color: menuButton.down ? "#8f263f9c"
                                   : menuButton.hovered ? "#ee252b88" : "#db151b64"
            border.color: menuButton.hovered ? root.gold : root.silver
            border.width: menuButton.hovered ? 4 : 3
            Behavior on color { ColorAnimation { duration: 150 } }
        }
    }

    function loadEditorFields() {
        root.loadingEditor = true
        questionField.text = controller.editorQuestionText
        answerA.text = controller.editorAnswers[0]
        answerB.text = controller.editorAnswers[1]
        answerC.text = controller.editorAnswers[2]
        answerD.text = controller.editorAnswers[3]
        correctBox.currentIndex = controller.editorCorrectIndex
        root.editorDirty = false
        root.loadingEditor = false
    }

    function openEditor() {
        root.loadEditorFields()
        editorShade.visible = true
        questionField.forceActiveFocus()
    }

    function openEditOptions() {
        editChoiceShade.visible = true
    }

    function openImport() {
        editChoiceShade.visible = false
        importShade.visible = true
    }

    function markEditorDirty() {
        if (!root.loadingEditor)
            root.editorDirty = true
    }

    function runEditorAction(action) {
        if (root.editorDirty) {
            root.pendingEditorAction = action
            discardShade.visible = true
        } else {
            action()
        }
    }

    function closeEditor() {
        root.runEditorAction(function() {
            editorShade.visible = false
        })
    }

    function startFromMenu() {
        root.menuVisible = false
        controller.startGame()
    }

    function answerColor(index) {
        let currentRevision = controller.revision
        if (controller.state === "answered") {
            if (index === controller.correctIndex)
                return "#16833d"
            if (index === controller.selectedIndex)
                return "#a8232f"
        }
        return root.royal
    }

    Image {
        anchors.fill: parent
        source: controller.backgroundUrl
        fillMode: Image.Stretch
        smooth: true
    }

    Rectangle {
        anchors.fill: parent
        color: "#1800092f"
    }

    Row {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 18
        spacing: 10
        z: 10

        TopButton {
            text: "Inicio"
            onClicked: {
                root.menuVisible = true
                controller.returnToMenu()
            }
        }
        TopButton {
            text: root.visibility === Window.FullScreen ? "Ventana" : "Pantalla completa"
            onClicked: root.visibility = root.visibility === Window.FullScreen
                       ? Window.Windowed : Window.FullScreen
        }
        TopButton {
            text: "Editar pregunta"
            onClicked: root.openEditor()
        }
        TopButton {
            text: "Reiniciar"
            onClicked: controller.startGame()
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: 18
        width: Math.max(300, root.width * 0.27)
        height: 38
        radius: height / 2
        color: "#c40a0d35"
        border.color: root.silver
        border.width: 2
        z: 10

        Text {
            anchors.centerIn: parent
            text: "Ronda " + controller.roundNumber + "  ·  Pregunta "
                  + controller.questionNumber + " de " + controller.roundQuestionCount
                  + "  ·  Aciertos " + controller.score
            color: "white"
            font.bold: true
            font.pixelSize: 13
        }
    }

    Column {
        id: lifelines
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.leftMargin: Math.max(28, parent.width * 0.035)
        anchors.topMargin: parent.height * 0.17
        spacing: Math.max(10, parent.height * 0.016)
        z: 5

        Button {
            id: fiftyButton
            width: Math.max(74, root.height * 0.105)
            height: width
            enabled: controller.state === "playing"
                     && controller.usedLifelines.indexOf("fifty") === -1
            opacity: enabled ? 1 : 0.38
            contentItem: Label {
                text: "50:50"
                color: "white"
                font.bold: true
                font.pixelSize: fiftyButton.width * 0.22
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                radius: width / 2
                color: root.navy
                border.color: root.silver
                border.width: 4
            }
            onClicked: controller.useFiftyFifty()
            ToolTip.visible: hovered
            ToolTip.text: "Eliminar dos respuestas incorrectas"
        }

        Button {
            id: phoneButton
            width: fiftyButton.width
            height: width
            enabled: controller.state === "playing"
                     && controller.usedLifelines.indexOf("phone") === -1
            opacity: enabled ? 1 : 0.38
            contentItem: Rectangle {
                color: root.silver
                radius: width / 2
                anchors.margins: phoneButton.width * 0.14
                Image {
                    anchors.fill: parent
                    anchors.margins: phoneButton.width * 0.12
                    source: controller.phoneIconUrl
                    fillMode: Image.PreserveAspectFit
                }
            }
            background: Rectangle {
                radius: width / 2
                color: root.navy
                border.color: root.silver
                border.width: 4
            }
            onClicked: controller.usePhone()
            ToolTip.visible: hovered
            ToolTip.text: "Comodín de llamada"
        }

        Button {
            id: audienceButton
            width: fiftyButton.width
            height: width
            enabled: controller.state === "playing"
                     && controller.usedLifelines.indexOf("audience") === -1
            opacity: enabled ? 1 : 0.38
            contentItem: Rectangle {
                color: root.silver
                radius: width / 2
                anchors.margins: audienceButton.width * 0.14
                Image {
                    anchors.fill: parent
                    anchors.margins: audienceButton.width * 0.10
                    source: controller.audienceIconUrl
                    fillMode: Image.PreserveAspectFit
                }
            }
            background: Rectangle {
                radius: width / 2
                color: root.navy
                border.color: root.silver
                border.width: 4
            }
            onClicked: controller.useAudience()
            ToolTip.visible: hovered
            ToolTip.text: "Comodín de público"
        }
    }

    Rectangle {
        id: timerCircle
        width: Math.max(88, root.height * 0.125)
        height: width
        radius: width / 2
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.rightMargin: Math.max(40, parent.width * 0.05)
        anchors.topMargin: parent.height * 0.29
        color: "#c10b1b6d"
        border.color: controller.countdownActive ? root.gold : root.silver
        border.width: 5

        Text {
            anchors.centerIn: parent
            text: controller.countdownActive ? controller.countdown : "—"
            color: controller.countdown <= 5 && controller.countdownActive
                   ? "#ffcf4b" : "white"
            font.bold: true
            font.pixelSize: timerCircle.width * 0.42
        }
    }

    Rectangle {
        id: questionFrame
        width: parent.width * 0.90
        height: Math.max(100, parent.height * 0.16)
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: answersGrid.top
        anchors.bottomMargin: 16
        radius: height * 0.28
        color: "#de132378"
        border.color: root.silver
        border.width: 3

        Text {
            anchors.fill: parent
            anchors.leftMargin: questionFrame.width * 0.06
            anchors.rightMargin: questionFrame.width * 0.06
            anchors.topMargin: 10
            anchors.bottomMargin: 10
            text: controller.questionText
            color: "white"
            font.pixelSize: Math.max(21, root.height * 0.038)
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
            minimumPixelSize: 17
            fontSizeMode: Text.Fit
        }
    }

    Grid {
        id: answersGrid
        columns: 2
        spacing: Math.max(10, root.width * 0.012)
        width: parent.width * 0.92
        height: Math.max(138, parent.height * 0.205)
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: statusPanel.top
        anchors.bottomMargin: 10

        Repeater {
            model: controller.answers

            Button {
                id: answerButton
                required property int index
                required property string modelData
                width: (answersGrid.width - answersGrid.spacing) / 2
                height: (answersGrid.height - answersGrid.spacing) / 2
                hoverEnabled: false
                enabled: controller.state === "playing"
                         && controller.hiddenIndices.indexOf(index) === -1
                opacity: controller.hiddenIndices.indexOf(index) === -1 ? 1 : 0

                onClicked: controller.selectAnswer(index)

                background: Rectangle {
                    radius: height * 0.35
                    color: root.answerColor(answerButton.index)
                    border.color: answerButton.index === controller.selectedIndex
                                  ? root.gold : root.silver
                    border.width: answerButton.index === controller.selectedIndex ? 4 : 2
                    Behavior on color {
                        ColorAnimation { duration: 300 }
                    }
                    Behavior on opacity {
                        NumberAnimation { duration: 250 }
                    }
                }

                contentItem: RowLayout {
                    spacing: 10
                    Rectangle {
                        Layout.preferredWidth: answerButton.height * 0.70
                        Layout.preferredHeight: answerButton.height * 0.70
                        radius: width / 2
                        color: root.navy
                        border.color: root.silver
                        border.width: 2
                        Label {
                            anchors.centerIn: parent
                            text: "ABCD"[answerButton.index]
                            color: "white"
                            font.bold: true
                            font.pixelSize: parent.height * 0.42
                        }
                    }
                    Label {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.rightMargin: 14
                        text: answerButton.modelData
                        color: "white"
                        font.pixelSize: Math.max(16, root.height * 0.026)
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        wrapMode: Text.WordWrap
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }

    Rectangle {
        id: statusPanel
        width: controller.canAdvance ? parent.width * 0.62 : parent.width * 0.80
        height: Math.max(36, parent.height * 0.055)
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 8
        radius: height / 2
        color: "#c20a0d35"
        border.color: "#6b6fa8"
        border.width: 1

        Text {
            anchors.fill: parent
            anchors.leftMargin: 20
            anchors.rightMargin: 20
            text: controller.message
            color: "#f3f3ff"
            font.pixelSize: Math.max(14, root.height * 0.022)
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
    }

    TopButton {
        anchors.left: statusPanel.right
        anchors.leftMargin: 12
        anchors.verticalCenter: statusPanel.verticalCenter
        visible: controller.canAdvance
        text: controller.isLastQuestion ? "Ver resultado" : "Siguiente pregunta"
        onClicked: controller.nextQuestion()
        z: 10
    }

    Item {
        id: menuView
        objectName: "menuView"
        anchors.fill: parent
        visible: root.menuVisible
        z: 90

        Image {
            anchors.fill: parent
            source: controller.menuBackgroundUrl
            fillMode: Image.PreserveAspectCrop
            smooth: true
            mipmap: true
        }

        Rectangle {
            anchors.fill: parent
            color: "#24000825"
        }

        Column {
            width: parent.width
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: Math.max(54, parent.height * 0.075)
            spacing: Math.max(14, parent.height * 0.022)

            Text {
                width: parent.width * 0.86
                anchors.horizontalCenter: parent.horizontalCenter
                text: "¿QUIÉN QUIERE SER MILLONARIO?"
                color: "white"
                font.bold: true
                font.pixelSize: Math.max(27, root.height * 0.052)
                horizontalAlignment: Text.AlignHCenter
                style: Text.Outline
                styleColor: "#37003f8f"
            }

            Text {
                width: parent.width * 0.8
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Edición privada y educativa · Banco de hasta 12 preguntas"
                color: "#e6e7ff"
                font.pixelSize: Math.max(15, root.height * 0.024)
                horizontalAlignment: Text.AlignHCenter
            }

            Item { width: 1; height: 3 }

            MenuButton {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Iniciar juego"
                onClicked: root.startFromMenu()
            }

            MenuButton {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Editar preguntas"
                onClicked: root.openEditOptions()
            }
        }
    }

    Item {
        id: finishView
        objectName: "finishView"
        anchors.fill: parent
        visible: controller.gameFinished
        z: 95

        Image {
            anchors.fill: parent
            source: controller.menuBackgroundUrl
            fillMode: Image.PreserveAspectCrop
            smooth: true
            mipmap: true
        }
        Rectangle {
            anchors.fill: parent
            color: "#82000825"
        }
        Rectangle {
            width: Math.min(parent.width * 0.72, 820)
            height: Math.min(parent.height * 0.56, 440)
            anchors.centerIn: parent
            radius: 24
            color: "#e80d1235"
            border.color: root.silver
            border.width: 3

            Column {
                anchors.fill: parent
                anchors.margins: 34
                spacing: 22

                Text {
                    width: parent.width
                    text: "RONDA FINALIZADA"
                    color: "white"
                    font.bold: true
                    font.pixelSize: Math.max(30, root.height * 0.06)
                    horizontalAlignment: Text.AlignHCenter
                }
                Text {
                    width: parent.width
                    text: controller.score + " de " + controller.roundQuestionCount
                    color: root.gold
                    font.bold: true
                    font.pixelSize: Math.max(54, root.height * 0.12)
                    horizontalAlignment: Text.AlignHCenter
                }
                Text {
                    width: parent.width
                    text: "respuestas correctas"
                    color: "#e6e7ff"
                    font.pixelSize: Math.max(18, root.height * 0.034)
                    horizontalAlignment: Text.AlignHCenter
                }
                Item { width: 1; height: 4 }
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 16
                    TopButton {
                        text: "Volver al inicio"
                        onClicked: {
                            controller.returnToMenu()
                            root.menuVisible = true
                        }
                    }
                    TopButton {
                        text: "Jugar nuevamente"
                        onClicked: {
                            root.menuVisible = false
                            controller.startGame()
                        }
                    }
                }
            }
        }
    }

    FileDialog {
        id: excelFileDialog
        title: "Seleccionar banco de preguntas"
        nameFilters: ["Archivos Excel (*.xlsx)"]
        onAccepted: {
            root.pendingExcelFile = selectedFile
            root.importSucceeded = false
        }
    }

    Rectangle {
        id: editChoiceShade
        objectName: "editChoiceShade"
        anchors.fill: parent
        visible: false
        color: "#c0000015"
        z: 105

        MouseArea {
            anchors.fill: parent
            onClicked: {}
        }

        Rectangle {
            width: Math.min(parent.width * 0.62, 720)
            height: Math.min(parent.height * 0.64, 440)
            anchors.centerIn: parent
            radius: 22
            color: "#f20d1235"
            border.color: "#858bc0"
            border.width: 2

            Column {
                anchors.fill: parent
                anchors.margins: 34
                spacing: 18

                Text {
                    width: parent.width
                    text: "EDITAR PREGUNTAS"
                    color: "white"
                    font.bold: true
                    font.pixelSize: 28
                    horizontalAlignment: Text.AlignHCenter
                }
                Text {
                    width: parent.width
                    text: "Elige cómo quieres administrar el banco del juego."
                    color: "#dfe1ff"
                    font.pixelSize: 16
                    horizontalAlignment: Text.AlignHCenter
                }
                Item { width: 1; height: 4 }
                MenuButton {
                    anchors.horizontalCenter: parent.horizontalCenter
                    implicitWidth: Math.min(parent.width, 560)
                    implicitHeight: 72
                    text: "Administrador manual"
                    onClicked: {
                        editChoiceShade.visible = false
                        root.openEditor()
                    }
                }
                MenuButton {
                    anchors.horizontalCenter: parent.horizontalCenter
                    implicitWidth: Math.min(parent.width, 560)
                    implicitHeight: 72
                    text: "Importar banco desde Excel"
                    onClicked: root.openImport()
                }
                TopButton {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Cancelar"
                    onClicked: editChoiceShade.visible = false
                }
            }
        }
    }

    Rectangle {
        id: importShade
        objectName: "importShade"
        anchors.fill: parent
        visible: false
        color: "#c0000015"
        z: 110

        MouseArea {
            anchors.fill: parent
            onClicked: {}
        }

        Rectangle {
            width: Math.min(parent.width * 0.72, 820)
            height: Math.min(parent.height * 0.72, 510)
            anchors.centerIn: parent
            radius: 22
            color: "#f20d1235"
            border.color: "#858bc0"
            border.width: 2

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 30
                spacing: 14

                Label {
                    text: "Importar banco desde Excel"
                    color: "white"
                    font.bold: true
                    font.pixelSize: 27
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    text: "Utiliza la plantilla incluida. Se aceptan entre 4 y 12 preguntas activas."
                    color: "#dfe1ff"
                    font.pixelSize: 16
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 86
                    radius: 10
                    color: "#171c44"
                    border.color: root.pendingExcelFile.toString() ? root.gold : "#59608f"
                    border.width: root.pendingExcelFile.toString() ? 2 : 1

                    Label {
                        anchors.fill: parent
                        anchors.margins: 14
                        text: root.pendingExcelFile.toString()
                              ? root.pendingExcelFile.toString().replace("file:///", "")
                              : "Todavía no se ha seleccionado un archivo."
                        color: root.pendingExcelFile.toString() ? "white" : "#9ea5d4"
                        wrapMode: Text.WrapAnywhere
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    TopButton {
                        text: "Seleccionar archivo Excel"
                        Layout.fillWidth: true
                        onClicked: excelFileDialog.open()
                    }
                    TopButton {
                        text: "Abrir carpeta de plantilla"
                        Layout.fillWidth: true
                        onClicked: controller.openTemplateFolder()
                    }
                }

                Label {
                    text: controller.importStatus
                    visible: text.length > 0
                    color: root.importSucceeded ? "#8fd5a7" : "#e9c16d"
                    font.bold: true
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                }

                Item { Layout.fillHeight: true }

                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    TopButton {
                        text: "Volver"
                        onClicked: {
                            importShade.visible = false
                            editChoiceShade.visible = true
                        }
                    }
                    TopButton {
                        text: "Cargar banco"
                        enabled: controller.projectWritable
                                 && root.pendingExcelFile.toString().length > 0
                        onClicked: {
                            root.importSucceeded = controller.importQuestionsFromExcel(
                                root.pendingExcelFile.toString()
                            )
                        }
                    }
                    TopButton {
                        text: root.importSucceeded ? "Abrir administrador" : "Cerrar"
                        onClicked: {
                            importShade.visible = false
                            if (root.importSucceeded)
                                root.openEditor()
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        id: editorShade
        objectName: "editorShade"
        anchors.fill: parent
        visible: false
        color: "#c0000015"
        z: 100

        MouseArea {
            anchors.fill: parent
            onClicked: {}
        }

        Rectangle {
            id: editorPanel
            width: Math.min(parent.width * 0.94, 1120)
            height: Math.min(parent.height * 0.94, 720)
            anchors.centerIn: parent
            radius: 18
            color: "#f20d1235"
            border.color: "#858bc0"
            border.width: 2

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 24
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        text: "Administrador de preguntas"
                        color: "white"
                        font.bold: true
                        font.pixelSize: 25
                        Layout.fillWidth: true
                    }
                    Label {
                        text: !controller.projectWritable ? "Solo lectura"
                              : root.editorDirty ? "Cambios sin guardar" : "Cambios guardados"
                        color: !controller.projectWritable ? "#e36770"
                               : root.editorDirty ? root.gold : "#8fd5a7"
                        font.bold: true
                    }
                    TopButton {
                        text: "Cerrar"
                        onClicked: root.closeEditor()
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 16

                    Rectangle {
                        Layout.preferredWidth: Math.min(editorPanel.width * 0.32, 340)
                        Layout.fillHeight: true
                        radius: 12
                        color: "#b4090d2b"
                        border.color: "#59608f"
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 8

                            Label {
                                text: "Banco · " + controller.bankQuestionCount
                                      + " / 12 preguntas"
                                color: "white"
                                font.bold: true
                                font.pixelSize: 17
                            }

                            ListView {
                                id: questionList
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                spacing: 6
                                model: controller.questionSummaries
                                currentIndex: controller.editorIndex

                                delegate: Button {
                                    id: questionDelegate
                                    required property int index
                                    required property string modelData
                                    width: questionList.width
                                    height: 58
                                    hoverEnabled: true
                                    onClicked: root.runEditorAction(function() {
                                        if (controller.selectEditorQuestion(questionDelegate.index))
                                            root.loadEditorFields()
                                    })
                                    contentItem: Label {
                                        text: questionDelegate.modelData
                                        color: "white"
                                        font.bold: questionDelegate.index === controller.editorIndex
                                        font.pixelSize: 13
                                        elide: Text.ElideRight
                                        wrapMode: Text.WordWrap
                                        maximumLineCount: 2
                                        verticalAlignment: Text.AlignVCenter
                                        leftPadding: 10
                                        rightPadding: 10
                                    }
                                    background: Rectangle {
                                        radius: 8
                                        color: questionDelegate.index === controller.editorIndex
                                               ? "#30358a" : questionDelegate.hovered
                                                 ? "#20265f" : "#151a40"
                                        border.color: questionDelegate.index === controller.editorIndex
                                                      ? root.gold : "#59608f"
                                        border.width: questionDelegate.index === controller.editorIndex ? 2 : 1
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                TopButton {
                                    text: "+ Nueva"
                                    Layout.fillWidth: true
                                    enabled: controller.projectWritable
                                             && controller.bankQuestionCount < 12
                                    onClicked: root.runEditorAction(function() {
                                        if (controller.addQuestion())
                                            root.loadEditorFields()
                                    })
                                }
                                TopButton {
                                    text: "Duplicar"
                                    Layout.fillWidth: true
                                    enabled: controller.projectWritable
                                             && controller.bankQuestionCount < 12
                                    onClicked: root.runEditorAction(function() {
                                        if (controller.duplicateQuestion())
                                            root.loadEditorFields()
                                    })
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                TopButton {
                                    text: "↑"
                                    enabled: controller.projectWritable && controller.editorIndex > 0
                                    onClicked: root.runEditorAction(function() {
                                        if (controller.moveQuestion(-1))
                                            root.loadEditorFields()
                                    })
                                }
                                TopButton {
                                    text: "↓"
                                    enabled: controller.projectWritable
                                             && controller.editorIndex < controller.bankQuestionCount - 1
                                    onClicked: root.runEditorAction(function() {
                                        if (controller.moveQuestion(1))
                                            root.loadEditorFields()
                                    })
                                }
                                Item { Layout.fillWidth: true }
                                TopButton {
                                    text: "Eliminar"
                                    enabled: controller.projectWritable
                                             && controller.bankQuestionCount > 1
                                    onClicked: deleteShade.visible = true
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 12
                        color: "#9a11163b"
                        border.color: "#59608f"
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 8

                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: "Pregunta " + (controller.editorIndex + 1)
                                    color: "#dfe1ff"
                                    font.bold: true
                                    font.pixelSize: 17
                                    Layout.fillWidth: true
                                }
                                Label {
                                    text: questionField.length + " / 320"
                                    color: "#9ea5d4"
                                }
                            }

                            TextArea {
                                id: questionField
                                enabled: controller.projectWritable
                                Layout.fillWidth: true
                                Layout.preferredHeight: 100
                                wrapMode: TextEdit.WordWrap
                                selectByMouse: true
                                color: "white"
                                selectionColor: root.royal
                                selectedTextColor: "white"
                                font.pixelSize: 16
                                leftPadding: 12
                                rightPadding: 12
                                topPadding: 10
                                bottomPadding: 10
                                onTextChanged: {
                                    if (length > 320)
                                        remove(320, length)
                                    root.markEditorDirty()
                                }
                                background: Rectangle {
                                    radius: 8
                                    color: questionField.activeFocus ? "#222958" : "#171c44"
                                    border.color: questionField.activeFocus ? root.gold : "#737aa8"
                                    border.width: questionField.activeFocus ? 2 : 1
                                }
                            }

                            Label {
                                text: "Alternativas"
                                color: "#dfe1ff"
                                font.bold: true
                            }
                            EditorField {
                                id: answerA
                                enabled: controller.projectWritable
                                Layout.fillWidth: true
                                placeholderText: "Alternativa A"
                                selectByMouse: true
                                maximumLength: 140
                                onTextChanged: root.markEditorDirty()
                            }
                            EditorField {
                                id: answerB
                                enabled: controller.projectWritable
                                Layout.fillWidth: true
                                placeholderText: "Alternativa B"
                                selectByMouse: true
                                maximumLength: 140
                                onTextChanged: root.markEditorDirty()
                            }
                            EditorField {
                                id: answerC
                                enabled: controller.projectWritable
                                Layout.fillWidth: true
                                placeholderText: "Alternativa C"
                                selectByMouse: true
                                maximumLength: 140
                                onTextChanged: root.markEditorDirty()
                            }
                            EditorField {
                                id: answerD
                                enabled: controller.projectWritable
                                Layout.fillWidth: true
                                placeholderText: "Alternativa D"
                                selectByMouse: true
                                maximumLength: 140
                                onTextChanged: root.markEditorDirty()
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: "Respuesta correcta"
                                    color: "#dfe1ff"
                                    font.bold: true
                                }
                                ComboBox {
                                    id: correctBox
                                    enabled: controller.projectWritable
                                    model: ["A", "B", "C", "D"]
                                    onCurrentIndexChanged: root.markEditorDirty()
                                    contentItem: Label {
                                        leftPadding: 10
                                        text: correctBox.displayText
                                        color: "white"
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                    background: Rectangle {
                                        radius: 7
                                        color: "#171c44"
                                        border.color: "#737aa8"
                                        border.width: 1
                                    }
                                }
                                Item { Layout.fillWidth: true }
                                Label {
                                    text: "Máximo 140 caracteres por respuesta"
                                    color: "#9ea5d4"
                                    font.pixelSize: 12
                                }
                            }

                            Item { Layout.fillHeight: true }

                            Label {
                                Layout.fillWidth: true
                                text: controller.message
                                color: "#bfc4ee"
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        text: "Archivo: " + controller.projectPath
                              + (controller.projectWritable ? "" : " · Unidad sin permiso de escritura")
                        color: "#8f96c2"
                        font.pixelSize: 11
                        elide: Text.ElideMiddle
                        Layout.fillWidth: true
                    }
                    TopButton {
                        text: "Cancelar"
                        onClicked: root.closeEditor()
                    }
                    TopButton {
                        text: "Guardar cambios"
                        highlighted: true
                        enabled: root.editorDirty && controller.projectWritable
                        onClicked: {
                            const saved = controller.saveQuestion(
                                questionField.text,
                                answerA.text,
                                answerB.text,
                                answerC.text,
                                answerD.text,
                                correctBox.currentIndex
                            )
                            if (saved) {
                                root.editorDirty = false
                                root.loadEditorFields()
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            id: discardShade
            anchors.fill: parent
            visible: false
            color: "#b0000015"
            z: 210

            Rectangle {
                width: Math.min(parent.width * 0.48, 520)
                height: 220
                anchors.centerIn: parent
                radius: 16
                color: "#fa11163b"
                border.color: root.gold
                border.width: 2

                Column {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 20
                    Text {
                        width: parent.width
                        text: "Hay cambios sin guardar"
                        color: "white"
                        font.bold: true
                        font.pixelSize: 23
                        horizontalAlignment: Text.AlignHCenter
                    }
                    Text {
                        width: parent.width
                        text: "Si continúas, los cambios de esta pregunta se descartarán."
                        color: "#dfe1ff"
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                    }
                    Row {
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: 12
                        TopButton {
                            text: "Seguir editando"
                            onClicked: {
                                discardShade.visible = false
                                root.pendingEditorAction = null
                            }
                        }
                        TopButton {
                            text: "Descartar cambios"
                            onClicked: {
                                const action = root.pendingEditorAction
                                root.pendingEditorAction = null
                                root.editorDirty = false
                                discardShade.visible = false
                                if (action)
                                    action()
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            id: deleteShade
            anchors.fill: parent
            visible: false
            color: "#b0000015"
            z: 220

            Rectangle {
                width: Math.min(parent.width * 0.46, 500)
                height: 210
                anchors.centerIn: parent
                radius: 16
                color: "#fa11163b"
                border.color: "#e36770"
                border.width: 2

                Column {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 20
                    Text {
                        width: parent.width
                        text: "¿Eliminar la pregunta " + (controller.editorIndex + 1) + "?"
                        color: "white"
                        font.bold: true
                        font.pixelSize: 22
                        horizontalAlignment: Text.AlignHCenter
                    }
                    Text {
                        width: parent.width
                        text: "Se creará un respaldo del archivo antes de eliminarla."
                        color: "#dfe1ff"
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                    }
                    Row {
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: 12
                        TopButton {
                            text: "Cancelar"
                            onClicked: deleteShade.visible = false
                        }
                        TopButton {
                            text: "Eliminar"
                            onClicked: {
                                deleteShade.visible = false
                                if (controller.deleteQuestion())
                                    root.loadEditorFields()
                            }
                        }
                    }
                }
            }
        }
    }

    Shortcut {
        sequence: "F11"
        onActivated: root.visibility = root.visibility === Window.FullScreen
                     ? Window.Windowed : Window.FullScreen
    }
    Shortcut {
        sequence: "Ctrl+E"
        onActivated: root.openEditor()
    }
    Shortcut {
        sequence: "Escape"
        onActivated: {
            if (editorShade.visible)
                root.closeEditor()
            else if (root.visibility === Window.FullScreen)
                root.visibility = Window.Windowed
        }
    }
}
