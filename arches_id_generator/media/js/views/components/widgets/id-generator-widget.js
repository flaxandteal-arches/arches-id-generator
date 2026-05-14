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

    if (ko.isObservable(self.auto_populate)) {
        self.auto_populate.subscribe(markDirty);
    }
    if (ko.isObservable(self.generate_on)) {
        self.generate_on.subscribe(markDirty);
    }
};

export default ko.components.register('id-generator-widget', {
    viewModel: viewModel,
    template: idGeneratorTemplate,
});
