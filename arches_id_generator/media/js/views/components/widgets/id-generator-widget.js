import ko from "knockout";
import WidgetViewModel from "viewmodels/widget";
import arches from "arches";
import idGeneratorTemplate from "templates/views/components/widgets/id-generator-widget.htm";

const viewModel = function(params) {
    params.configKeys = ["sequence_key", "template", "default_placeholder"];
    WidgetViewModel.apply(this, [params]);
    const self = this;

    self.displayValue = ko.computed(() =>
        ko.unwrap(ko.unwrap(self.value)?.[arches.activeLanguage]?.value) ?? ""
    );

};

export default ko.components.register('id-generator-widget', {
    viewModel: viewModel,
    template: idGeneratorTemplate,
});
