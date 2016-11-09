(function($) {
	/**
	 * インジケータ表示範囲を管理するコントローラ
	 *
	 * @class indicatorController
	 */
	var indicatorController = {
		__name: 'indicatorAllController',

		/**
		 * インジケータ表示ボタン押下イベント
		 *
		 * @memberOf indicatorController
		 */
		'#indicator click': function(){

			//インジケータ表示
			var indicator = this.indicator({
				message: '<h2>フィードバックを反映しています。</h2>',
				target : document.body
			}).show();

			/*setTimeout(function() {

				//インジケータ除去
				indicator.hide();

			}, 30000);*/

		}
	};
	$(function(){
		h5.core.controller('#indicator-target', indicatorController);
	})

})(jQuery);

