import ko from "knockout";
import WidgetViewModel from "viewmodels/widget";
import arches from "arches";
import idGeneratorTemplate from "templates/views/components/widgets/id-generator-widget.htm";

const viewModel = function(params) {
    params.configKeys = ["sequence_key", "template", "default_placeholder", "auto_populate"];
    WidgetViewModel.apply(this, [params]);
    const self = this;

    self.displayValue = ko.computed(() =>
        ko.unwrap(ko.unwrap(self.value)?.[arches.activeLanguage]?.value) ?? ""
    );
    console.log("[id-generator] init", {
        configKeys: self.configKeys,
        config: ko.toJS(self.config),
        auto_populate_isObservable: ko.isObservable(self.auto_populate),
        auto_populate_initialValue: ko.unwrap(self.auto_populate),
        hasDirtyWidget: typeof params.graphDesignerHasDirtyWidget,
    });

    if (ko.isObservable(self.auto_populate)) {
        self.auto_populate.subscribe((val) => {
            console.log("[id-generator] auto_populate changed →", val,
                "config now:", ko.toJS(self.config));
            if (typeof params.graphDesignerHasDirtyWidget === "function") {
                params.graphDesignerHasDirtyWidget(true);
            }
        });
    }
};

export default ko.components.register('id-generator-widget', {
    viewModel: viewModel,
    template: idGeneratorTemplate,
});
