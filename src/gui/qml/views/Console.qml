pragma ComponentBehavior: Bound
import QtCore
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import qml.components

ColumnLayout {
    id: root

    required property SystemPalette systemPalette
    required property AbstractListModel logModel
    required property QtObject pathModel
    required property string emojiFontFamily
    required property string monospaceFontFamily

    Settings {
        id: settings

        category: "Console"
        location: root.pathModel.get_preferences_path("Console.ini")

        property bool autoScroll: true
    }

    RowLayout {
        Layout.fillWidth: true

        Text {
            Layout.fillWidth: true
            Layout.leftMargin: 10
            Layout.topMargin: 5
            Layout.bottomMargin: 5

            text: "Log"
            color: root.systemPalette.text
        }
        CustomButton {
            Layout.alignment: Qt.AlignRight

            systemPalette: root.systemPalette
            text: `<font face="${root.emojiFontFamily}">⏬</font> Autoscroll`
            palette.buttonText: settings.autoScroll ? root.systemPalette.buttonText : root.systemPalette.placeholderText
            onClicked: settings.autoScroll = !settings.autoScroll
        }
        CustomButton {
            Layout.alignment: Qt.AlignRight

            systemPalette: root.systemPalette
            text: `<font face="${root.emojiFontFamily}">📋</font> Copy`
            onClicked: root.logModel.copy_log()
        }
    }
    ListView {
        id: logList

        Layout.fillHeight: true
        Layout.fillWidth: true

        leftMargin: 10
        rightMargin: 10
        orientation: ListView.Vertical
        boundsBehavior: Flickable.StopAtBounds
        boundsMovement: Flickable.StopAtBounds
        clip: true
        highlightFollowsCurrentItem: false
        model: root.logModel
        delegate: SelectableText {
            id: logDelegate

            required property int index
            required property string message
            required property int severity

            width: logList.width
            color: root.systemPalette.text
            text: message
            font.family: root.monospaceFontFamily
            onLinkActivated: Qt.openUrlExternally(hoveredLink)

            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.NoButton // we don't want to eat clicks on the Text
                cursorShape: parent.hoveredLink ? Qt.PointingHandCursor : undefined
            }
        }

        onCountChanged: {
            if (settings.autoScroll)
                Qt.callLater(logList.positionViewAtEnd);
        }

        ScrollBar.vertical: ScrollBar {}
    }
}
