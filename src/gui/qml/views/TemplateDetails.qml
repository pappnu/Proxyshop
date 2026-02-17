pragma ComponentBehavior: Bound
import QtCore
import QtQml
import QtQuick
import QtQuick.Controls

import qml.components

Rectangle {
    id: templateDetails

    required property SystemPalette systemPalette
    required property AbstractListModel templateListMdl
    required property DelegateModel templateListDelegateMdl
    required property QtObject pathModel
    property var model: templateListDelegateMdl.items.count ? templateListDelegateMdl.items.get(templateListMdl.selected_index).model : undefined

    Settings {
        id: settings

        category: "TemplateDetails"
        location: templateDetails.pathModel.get_preferences_path("TemplateDetails.ini")

        property var detailsSplitState
    }

    Component.onCompleted: {
        detailsSplit.restoreState(settings.detailsSplitState);
    }
    Component.onDestruction: {
        settings.detailsSplitState = detailsSplit.saveState();
    }

    color: systemPalette.window

    SplitView {
        id: detailsSplit

        anchors.fill: parent
        orientation: Qt.Vertical

        Image {
            SplitView.fillWidth: true
            SplitView.preferredHeight: 270

            verticalAlignment: Image.AlignTop
            asynchronous: true
            source: templateDetails.model?.img ?? pathModel.preview_img_fallback
            fillMode: Image.PreserveAspectFit
        }
        ListView {
            id: detailsTextFields

            SplitView.fillWidth: true
            SplitView.fillHeight: true

            spacing: 2
            orientation: ListView.Vertical
            boundsBehavior: Flickable.StopAtBounds
            boundsMovement: Flickable.StopAtBounds
            clip: true
            highlightFollowsCurrentItem: false
            currentIndex: -1
            model: {
                const isPlugin = Boolean(templateDetails.model?.plugin);

                return [
                    {
                        name: "Name:",
                        isTitle: true,
                        isVisible: true
                    },
                    {
                        name: templateDetails.model?.name ?? "",
                        isTitle: false,
                        isVisible: true
                    },
                    {
                        name: "Plugin:",
                        isTitle: true,
                        isVisible: isPlugin
                    },
                    {
                        name: templateDetails.model?.plugin ?? "",
                        isTitle: false,
                        isVisible: isPlugin
                    },
                    {
                        name: "Supported layouts:",
                        isTitle: true,
                        isVisible: true
                    },
                    {
                        name: templateDetails.model?.card_layouts.join(", ") ?? "",
                        isTitle: false,
                        isVisible: true
                    },
                    {
                        name: "Installed templates:",
                        isTitle: true,
                        isVisible: true
                    },
                    {
                        name: templateDetails.model?.installed_template_files && templateDetails.model.installed_template_files.length ? templateDetails.model.installed_template_files.join(", ") : "None",
                        isTitle: false,
                        isVisible: true
                    },
                    {
                        name: "Missing templates:",
                        isTitle: true,
                        isVisible: true
                    },
                    {
                        name: templateDetails.model?.missing_template_files && templateDetails.model.missing_template_files.length ? templateDetails.model.missing_template_files.join(", ") : "None",
                        isTitle: false,
                        isVisible: true
                    }
                ];
            }
            delegate: SelectableText {
                id: textFieldDelegate

                required property int index
                property var item: detailsTextFields.model[index]
                property string name: item.name
                property bool isTitle: item.isTitle
                property bool isVisible: item.isVisible

                leftPadding: 5
                rightPadding: 5
                width: detailsTextFields.width
                text: name
                color: templateDetails.systemPalette.text
                font.bold: isTitle
                visible: isVisible

                Component.onCompleted: {
                    if (!isVisible) {
                        textFieldDelegate.height = -detailsTextFields.spacing;
                    }
                }
            }

            ScrollBar.vertical: ScrollBar {}
        }
    }
}
