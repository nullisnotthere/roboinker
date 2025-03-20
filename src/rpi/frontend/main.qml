import QtQuick 6.5
import QtQuick.Controls 6.5
import QtQuick.Layouts 6.5

ApplicationWindow {
    visible: true
    width: 600
    height: 1024
    flags:  Qt.Window | Qt.Tool
    title: "RoboInker GUI"

    ColumnLayout {
        spacing: 10
        anchors.centerIn: parent

        Text { text: "X Axis" }
        Slider {
            id: xSlider
            from: -200
            to: 200
            value: 0
            Layout.fillWidth: true
            onValueChanged: {
                onClicked: backend.update_axis("x", value)
            }
        }

        Text { text: "Y Axis" }
        Slider {
            id: ySlider
            from: -200
            to: 200
            value: 0
            Layout.fillWidth: true
            onValueChanged: {
                onClicked: backend.update_axis("y", value)
            }
        }

        Text { text: "Z Axis" }
        Slider {
            id: zSlider
            from: -200
            to: 200
            value: 0
            Layout.fillWidth: true
            onValueChanged: {
                onClicked: backend.update_axis("z", value)
            }
        }

        Text { text: "A (Pen) Axis" }
        Slider {
            id: aAxis
            from: -200
            to: 200
            value: 0
            Layout.fillWidth: true
            onValueChanged: {
                onClicked: backend.update_axis("a", value)
            }
        }

        Button {
            text: "Send data via Serial"
            onClicked: backend.send_serial()
        }
        Button {
            text: "Stop"
            onClicked: backend.stop_all_motors()
        }
    }
}

