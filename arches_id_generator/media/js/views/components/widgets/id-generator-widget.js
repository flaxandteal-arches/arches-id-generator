import ko from "knockout";
import WidgetViewModel from "viewmodels/widget";
import arches from "arches";
import idGeneratorTemplate from "templates/views/components/widgets/id-generator-widget.htm";

const viewModel = function(params) {
    params.configKeys = [
        "sequence_key",
        "template",
        "default_placeholder",
        "auto_populate",
        "generate_on",
    ];
    WidgetViewModel.apply(this, [params]);
    const self = this;

    self.displayValue = ko.computed(() =>
        ko.unwrap(ko.unwrap(self.value)?.[arches.activeLanguage]?.value) ?? ""
    );

    const markDirty = () => {
        if (typeof params.graphDesignerHasDirtyWidget === "function") {
            params.graphDesignerHasDirtyWidget(true);
        }
    };

    // Contradicts resource_activation (lifecycle creates the tile itself):
    // disable the checkbox and force it off.
    self.autoPopulateDisabled = ko.computed(() =>
        ko.unwrap(self.generate_on) === "resource_activation"
    );

    if (ko.isObservable(self.auto_populate)) {
        self.auto_populate.subscribe(markDirty);
    }
    if (ko.isObservable(self.generate_on)) {
        self.generate_on.subscribe(markDirty);
        self.generate_on.subscribe((value) => {
            if (value === "resource_activation" && ko.unwrap(self.auto_populate)) {
                self.auto_populate(false);
            }
        });
    }
};

export default ko.components.register('id-generator-widget', {
    viewModel: viewModel,
    template: idGeneratorTemplate,
});
