pragma ComponentBehavior: Bound
import QtCore
import QtQml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import qml.components

ApplicationWindow {
    id: templateUpdaterWindow

    required property SystemPalette systemPalette
    required property AbstractListModel updaterModel
    required property QtObject pathModel

    DelegateModel {
        id: updaterDelegateModel
        model: templateUpdaterWindow.updaterModel
    }

    // From https://stackoverflow.com/a/20732091
    function humanFileSize(bytes: int): string {
        const i = bytes === 0 ? 0 : Math.floor(Math.log(bytes) / Math.log(1024));
        return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${["B", "kB", "MB", "GB", "TB"][i]}`;
    }

    title: "Template updater"
    width: 800
    height: 640
    visible: true
    color: systemPalette.window

    Settings {
        id: settings

        category: "TemplateUpdater"
        location: templateUpdaterWindow.pathModel.get_preferences_path("TemplateUpdater.ini")

        property alias windowWidth: templateUpdaterWindow.width
        property alias windowHeight: templateUpdaterWindow.height
        property alias windowX: templateUpdaterWindow.x
        property alias windowY: templateUpdaterWindow.y

        property var updaterSplitState
    }

    Component.onCompleted: {
        updaterSplit.restoreState(settings.updaterSplitState);
        if (updaterDelegateModel.count < 1)
            updaterModel.fetch_data();
    }
    Component.onDestruction: {
        settings.updaterSplitState = updaterSplit.saveState();
    }

    SplitView {
        id: updaterSplit

        anchors.fill: parent
        orientation: Qt.Horizontal

        Loader {
            id: listLoader

            SplitView.fillHeight: true
            SplitView.fillWidth: true

            asynchronous: true
            sourceComponent: templateUpdaterWindow.updaterModel.fetching_data ? fetchingIndicatorComponent : availableTemplatesListComponent

            Component {
                id: fetchingIndicatorComponent

                Item {
                    BusyIndicator {
                        id: indicator

                        anchors.centerIn: parent
                        implicitWidth: 50
                        implicitHeight: 50
                        running: templateUpdaterWindow.updaterModel.fetching_data

                        palette.dark: templateUpdaterWindow.systemPalette.text
                    }
                }
            }
            Component {
                id: availableTemplatesListComponent

                ListView {
                    id: availableTemplatesList

                    orientation: ListView.Vertical
                    boundsBehavior: Flickable.StopAtBounds
                    boundsMovement: Flickable.StopAtBounds
                    reuseItems: true
                    clip: true
                    focus: true
                    highlight: Rectangle {
                        height: availableTemplatesList.currentItem?.height ?? 0
                        width: availableTemplatesList.currentItem?.width ?? 0
                        color: templateUpdaterWindow.systemPalette.highlight
                        y: availableTemplatesList.currentItem?.y ?? 0
                    }
                    highlightFollowsCurrentItem: false
                    currentIndex: templateUpdaterWindow.updaterModel.selected_index
                    model: updaterDelegateModel
                    delegate: CustomItemDelegate {
                        id: availableTemplatesListDelegate

                        required property int index
                        required property string file_name
                        required property string google_drive_id
                        required property string img
                        required property string plugin
                        required property list<string> template_names
                        required property list<string> template_classes
                        required property list<string> layout_categories
                        required property string installed_version
                        required property string available_version
                        required property int download_size
                        required property bool downloading

                        property bool canDownload: !installed_version && available_version
                        property bool hasUpdateAvailable: available_version && installed_version && (installed_version !== available_version)

                        systemPalette: templateUpdaterWindow.systemPalette
                        width: availableTemplatesList.width
                        height: 30
                        highlighted: false

                        onClicked: {
                            templateUpdaterWindow.updaterModel.selected_index = index;
                        }

                        contentItem: RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            spacing: 10

                            Text {
                                Layout.alignment: Qt.AlignLeft

                                text: availableTemplatesListDelegate.file_name + (availableTemplatesListDelegate.plugin ? ` (${availableTemplatesListDelegate.plugin})` : "")
                                color: availableTemplatesListDelegate.installed_version ? (templateUpdaterWindow.updaterModel.selected_index === availableTemplatesListDelegate.index ? templateUpdaterWindow.systemPalette.highlightedText : templateUpdaterWindow.systemPalette.text) : templateUpdaterWindow.systemPalette.placeholderText
                            }
                            CustomButton {
                                id: downloadButton

                                Layout.alignment: Qt.AlignRight

                                systemPalette: templateUpdaterWindow.systemPalette
                                text: {
                                    if (availableTemplatesListDelegate.downloading) {
                                        return "Downloading";
                                    }
                                    if (availableTemplatesListDelegate.hasUpdateAvailable) {
                                        return "Update";
                                    }
                                    if (availableTemplatesListDelegate.canDownload) {
                                        return "Download";
                                    }
                                    if (availableTemplatesListDelegate.installed_version) {
                                        return "Installed";
                                    }
                                    return "Unavailable";
                                }
                                enabled: !availableTemplatesListDelegate.downloading && (availableTemplatesListDelegate.canDownload || availableTemplatesListDelegate.hasUpdateAvailable)
                                onClicked: {
                                    templateUpdaterWindow.updaterModel.download_template(availableTemplatesListDelegate.index);
                                }
                            }
                        }
                    }

                    ScrollBar.vertical: ScrollBar {}
                }
            }
        }

        SplitView {
            id: selectedUpdaterItemDetails
            orientation: Qt.Vertical

            property var selectedItem: updaterDelegateModel.items.count ? updaterDelegateModel.items.get(templateUpdaterWindow.updaterModel.selected_index).model : undefined

            SplitView.fillHeight: true
            SplitView.preferredWidth: 200

            Image {
                SplitView.fillWidth: true
                SplitView.preferredHeight: 270

                verticalAlignment: Image.AlignTop
                asynchronous: true
                source: selectedUpdaterItemDetails.selectedItem?.img ?? templateUpdaterWindow.pathModel.preview_img_fallback
                fillMode: Image.PreserveAspectFit
            }

            ColumnLayout {
                SplitView.fillWidth: true

                SelectableText {
                    Layout.alignment: Qt.AlignTop
                    Layout.fillWidth: true

                    text: "<b>File name:</b>"
                    color: templateUpdaterWindow.systemPalette.text
                }
                SelectableText {
                    Layout.alignment: Qt.AlignTop
                    Layout.fillWidth: true

                    text: selectedUpdaterItemDetails.selectedItem?.file_name ?? ""
                    color: templateUpdaterWindow.systemPalette.text
                }

                SelectableText {
                    Layout.alignment: Qt.AlignTop
                    Layout.fillWidth: true

                    text: "<b>Installed version:</b>"
                    color: templateUpdaterWindow.systemPalette.text
                }
                SelectableText {
                    Layout.alignment: Qt.AlignTop
                    Layout.fillWidth: true

                    text: selectedUpdaterItemDetails.selectedItem?.installed_version || "Not installed"
                    color: templateUpdaterWindow.systemPalette.text
                }

                SelectableText {
                    Layout.alignment: Qt.AlignTop
                    Layout.fillWidth: true

                    text: "<b>Newest version:</b>"
                    color: templateUpdaterWindow.systemPalette.text
                }
                SelectableText {
                    Layout.alignment: Qt.AlignTop
                    Layout.fillWidth: true

                    text: selectedUpdaterItemDetails.selectedItem?.available_version ?? "Not available"
                    color: templateUpdaterWindow.systemPalette.text
                }

                SelectableText {
                    Layout.alignment: Qt.AlignTop
                    Layout.fillWidth: true

                    text: "<b>Download size:</b>"
                    color: templateUpdaterWindow.systemPalette.text
                }
                SelectableText {
                    Layout.alignment: Qt.AlignTop
                    Layout.fillWidth: true

                    text: templateUpdaterWindow.humanFileSize(selectedUpdaterItemDetails.selectedItem?.download_size ?? 0)
                    color: templateUpdaterWindow.systemPalette.text
                }

                SelectableText {
                    Layout.alignment: Qt.AlignTop
                    Layout.fillWidth: true

                    text: "<b>Template names:</b>"
                    wrapMode: Text.WordWrap
                    color: templateUpdaterWindow.systemPalette.text
                }
                SelectableText {
                    Layout.alignment: Qt.AlignTop
                    Layout.fillWidth: true

                    text: selectedUpdaterItemDetails.selectedItem?.template_names.join(", ") ?? ""
                    color: templateUpdaterWindow.systemPalette.text
                }

                SelectableText {
                    Layout.alignment: Qt.AlignTop
                    Layout.fillWidth: true

                    text: "<b>Template layouts:</b>"
                    color: templateUpdaterWindow.systemPalette.text
                }
                SelectableText {
                    Layout.alignment: Qt.AlignTop
                    Layout.fillWidth: true

                    text: selectedUpdaterItemDetails.selectedItem?.layout_categories.join(", ") ?? ""
                    color: templateUpdaterWindow.systemPalette.text
                }

                SelectableText {
                    Layout.alignment: Qt.AlignTop
                    Layout.fillWidth: true

                    text: "<b>Template classes:</b>"
                    color: templateUpdaterWindow.systemPalette.text
                }
                SelectableText {
                    Layout.alignment: Qt.AlignTop
                    Layout.fillWidth: true

                    text: selectedUpdaterItemDetails.selectedItem?.template_classes.join(", ") ?? ""
                    color: templateUpdaterWindow.systemPalette.text
                }

                Item {
                    Layout.fillHeight: true
                }
            }
        }
    }
}
